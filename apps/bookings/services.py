from datetime import date, datetime, timedelta
from decimal import Decimal
import secrets
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError
from apps.rooms.models import Room, RoomType
from .models import BookingHold, Reservation, BookingAuditLog


class BookingConflictError(Exception):
    """Raised when an overlapping confirmed reservation or active hold prevents booking."""
    pass


class InvalidDateRangeError(ValidationError):
    """Raised when check-in or check-out dates are invalid."""
    pass


class BookingService:
    @staticmethod
    def calculate_pricing(room_type, check_in, check_out, guests_count=1, has_breakfast=False, has_shuttle=False):
        """
        Calculates itemized pricing including nightly rates, weekend differentials,
        taxes (12%), resort service fee (5%), and optional hospitality addons.
        """
        if check_out <= check_in:
            raise InvalidDateRangeError("Check-out date must be strictly after check-in date.")

        num_nights = (check_out - check_in).days
        if num_nights > 90:
            raise InvalidDateRangeError("Maximum stay length is 90 nights.")

        # Compute per-night rate accounting for weekend pricing
        current_date = check_in
        nightly_rates = []
        base_rate = room_type.base_price
        weekend_rate = room_type.weekend_price or (base_rate * Decimal('1.15')).quantize(Decimal('0.01'))

        total_room_cost = Decimal('0.00')
        while current_date < check_out:
            # Friday (4) and Saturday (5) are weekend nights
            if current_date.weekday() in (4, 5):
                nightly_rates.append(weekend_rate)
                total_room_cost += weekend_rate
            else:
                nightly_rates.append(base_rate)
                total_room_cost += base_rate
            current_date += timedelta(days=1)

        average_nightly_rate = (total_room_cost / num_nights).quantize(Decimal('0.01'))

        # Addons
        addons_total = Decimal('0.00')
        addons_breakdown = []
        if has_breakfast:
            breakfast_fee = Decimal('25.00') * guests_count * num_nights
            addons_total += breakfast_fee
            addons_breakdown.append({
                'name': f'Artisan Breakfast Buffet ({guests_count} guests x {num_nights} nights)',
                'amount': breakfast_fee
            })
        if has_shuttle:
            shuttle_fee = Decimal('45.00')
            addons_total += shuttle_fee
            addons_breakdown.append({
                'name': 'Private Airport Shuttle Service (Round-trip)',
                'amount': shuttle_fee
            })

        # Taxes and Service fees
        tax_rate = Decimal(str(settings.HOTEL_SETTINGS.get('TAX_RATE_PERCENT', 12.0))) / Decimal('100')
        service_fee_rate = Decimal(str(settings.HOTEL_SETTINGS.get('SERVICE_FEE_PERCENT', 5.0))) / Decimal('100')

        tax_amount = (total_room_cost * tax_rate).quantize(Decimal('0.01'))
        service_fee = (total_room_cost * service_fee_rate).quantize(Decimal('0.01'))
        total_amount = total_room_cost + addons_total + tax_amount + service_fee

        return {
            'num_nights': num_nights,
            'average_nightly_rate': average_nightly_rate,
            'room_subtotal': total_room_cost,
            'nightly_rates': nightly_rates,
            'tax_rate_percent': settings.HOTEL_SETTINGS.get('TAX_RATE_PERCENT', 12.0),
            'tax_amount': tax_amount,
            'service_fee_percent': settings.HOTEL_SETTINGS.get('SERVICE_FEE_PERCENT', 5.0),
            'service_fee': service_fee,
            'addons_breakdown': addons_breakdown,
            'addons_total': addons_total,
            'total_amount': total_amount,
        }

    @staticmethod
    def get_available_rooms(check_in, check_out, guests_count=1, room_type_id=None):
        """
        Returns all active rooms available for the given date range.
        Accurately excludes:
          1. Overlapping CONFIRMED or CHECKED_IN reservations
          2. Active (unexpired & unconsumed) temporary holds
          3. Rooms currently in MAINTENANCE status
        """
        if check_out <= check_in:
            raise InvalidDateRangeError("Check-out date must be after check-in date.")

        now = timezone.now()

        # Find room IDs with overlapping confirmed or checked-in reservations
        reserved_room_ids = Reservation.objects.filter(
            status__in=[Reservation.Status.CONFIRMED, Reservation.Status.CHECKED_IN],
            check_in__lt=check_out,
            check_out__gt=check_in
        ).values_list('room_id', flat=True)

        # Find room IDs with active, non-expired temporary holds
        held_room_ids = BookingHold.objects.filter(
            is_consumed=False,
            expires_at__gt=now,
            check_in__lt=check_out,
            check_out__gt=check_in
        ).values_list('room_id', flat=True)

        blocked_ids = set(reserved_room_ids).union(set(held_room_ids))

        # Query operational rooms matching criteria
        available_rooms = Room.objects.filter(
            is_active=True,
            room_type__is_active=True,
            room_type__max_guests__gte=guests_count
        ).exclude(id__in=blocked_ids).exclude(status=Room.Status.MAINTENANCE)

        if room_type_id:
            available_rooms = available_rooms.filter(room_type_id=room_type_id)

        return available_rooms.select_related('room_type').prefetch_related('room_type__amenities')

    @classmethod
    def create_hold(cls, room_id, check_in, check_out, guests_count=1, guest_user=None, ip_address=''):
        """
        Creates a temporary hold for a specific room.
        Guarantees that other customers cannot book this room for 15 minutes.
        """
        with transaction.atomic():
            room = Room.objects.select_for_update().get(id=room_id)
            if not room.is_operational:
                raise BookingConflictError(f"Room {room.room_number} is currently out of service.")

            now = timezone.now()

            # Verify no overlapping confirmed reservation
            has_reservation = Reservation.objects.filter(
                room=room,
                status__in=[Reservation.Status.CONFIRMED, Reservation.Status.CHECKED_IN],
                check_in__lt=check_out,
                check_out__gt=check_in
            ).exists()
            if has_reservation:
                raise BookingConflictError(f"Room {room.room_number} has an existing reservation for these dates.")

            # Verify no active unexpired hold
            has_active_hold = BookingHold.objects.filter(
                room=room,
                is_consumed=False,
                expires_at__gt=now,
                check_in__lt=check_out,
                check_out__gt=check_in
            ).exists()
            if has_active_hold:
                raise BookingConflictError(f"Room {room.room_number} is temporarily held by another guest.")

            pricing = cls.calculate_pricing(room.room_type, check_in, check_out, guests_count)
            expiry_minutes = settings.HOTEL_SETTINGS.get('HOLD_EXPIRY_MINUTES', 15)
            expires_at = now + timedelta(minutes=expiry_minutes)

            hold = BookingHold.objects.create(
                room=room,
                room_type=room.room_type,
                guest=guest_user if guest_user and guest_user.is_authenticated else None,
                check_in=check_in,
                check_out=check_out,
                guests_count=guests_count,
                estimated_total=pricing['total_amount'],
                expires_at=expires_at
            )

            BookingAuditLog.objects.create(
                room=room,
                user=guest_user if guest_user and guest_user.is_authenticated else None,
                action=BookingAuditLog.Action.HOLD_CREATED,
                title=f"Hold created for Room {room.room_number}",
                details=f"Hold {hold.hold_id} reserved for {check_in} to {check_out}. Valid until {expires_at:%H:%M:%S UTC}.",
                ip_address=ip_address
            )

            return hold

    @classmethod
    def confirm_booking(cls, hold_id, guest_user, guest_details, payment_data=None, ip_address=''):
        """
        Atomically converts a hold into a confirmed reservation.
        Prevents concurrency race conditions using database row locks (select_for_update)
        and strict overlap queries inside transaction.atomic().
        """
        with transaction.atomic():
            try:
                hold = BookingHold.objects.select_for_update().get(hold_id=hold_id)
            except BookingHold.DoesNotExist:
                raise BookingConflictError("Hold token not found or expired.")

            if hold.is_consumed:
                raise BookingConflictError("This hold has already been converted to a reservation.")

            if hold.is_expired:
                BookingAuditLog.objects.create(
                    room=hold.room,
                    user=guest_user,
                    action=BookingAuditLog.Action.HOLD_EXPIRED,
                    title="Attempted booking with expired hold",
                    details=f"Hold {hold.hold_id} expired at {hold.expires_at}.",
                    ip_address=ip_address
                )
                raise BookingConflictError("Your 15-minute hold has expired. Please search again for current room availability.")

            # Lock the target room record to ensure concurrency integrity
            room = Room.objects.select_for_update().get(id=hold.room_id)

            # Re-verify no overlapping reservation was confirmed
            overlapping = Reservation.objects.filter(
                room=room,
                status__in=[Reservation.Status.CONFIRMED, Reservation.Status.CHECKED_IN],
                check_in__lt=hold.check_out,
                check_out__gt=hold.check_in
            )
            if overlapping.exists():
                raise BookingConflictError(f"Room {room.room_number} is no longer available for the selected dates.")

            # Calculate finalized pricing
            has_breakfast = payment_data.get('has_breakfast', False) if payment_data else False
            has_shuttle = payment_data.get('has_shuttle', False) if payment_data else False

            pricing = cls.calculate_pricing(
                room.room_type,
                hold.check_in,
                hold.check_out,
                hold.guests_count,
                has_breakfast=has_breakfast,
                has_shuttle=has_shuttle
            )

            # Generate unique booking reference: GV-YYYY-XXXX
            year = hold.check_in.year
            random_code = secrets.token_hex(3).upper()
            booking_ref = f"GV-{year}-{random_code}"
            while Reservation.objects.filter(booking_reference=booking_ref).exists():
                random_code = secrets.token_hex(3).upper()
                booking_ref = f"GV-{year}-{random_code}"

            # Simulated payment verification
            payment_method = payment_data.get('payment_method', 'CARD_SANDBOX') if payment_data else 'CARD_SANDBOX'
            mock_txn_id = f"TXN-SB-{secrets.token_hex(5).upper()}"

            reservation = Reservation.objects.create(
                booking_reference=booking_ref,
                guest=guest_user,
                guest_name=guest_details.get('name', guest_user.get_full_name() or guest_user.email),
                guest_email=guest_details.get('email', guest_user.email),
                guest_phone=guest_details.get('phone', guest_user.phone_number),
                special_requests=guest_details.get('special_requests', ''),
                room=room,
                room_type=room.room_type,
                check_in=hold.check_in,
                check_out=hold.check_out,
                guests_count=hold.guests_count,
                status=Reservation.Status.CONFIRMED,
                nightly_rate=pricing['average_nightly_rate'],
                num_nights=pricing['num_nights'],
                room_subtotal=pricing['room_subtotal'],
                tax_amount=pricing['tax_amount'],
                service_fee=pricing['service_fee'],
                addons_amount=pricing['addons_total'],
                total_amount=pricing['total_amount'],
                payment_status=Reservation.PaymentStatus.PAID,
                payment_method=payment_method,
                transaction_id=mock_txn_id,
                paid_at=timezone.now()
            )

            # Mark hold consumed
            hold.is_consumed = True
            hold.save(update_fields=['is_consumed'])

            # Log audit trail
            BookingAuditLog.objects.create(
                reservation=reservation,
                room=room,
                user=guest_user,
                action=BookingAuditLog.Action.BOOKING_CONFIRMED,
                title=f"Reservation {reservation.booking_reference} Confirmed",
                details=f"Confirmed for Room {room.room_number} ({hold.check_in} to {hold.check_out}). Total: ${reservation.total_amount}. Txn: {mock_txn_id}.",
                ip_address=ip_address
            )

            return reservation

    @classmethod
    def check_in_guest(cls, reservation_id, staff_user, ip_address=''):
        """
        Staff action: Check in an arriving guest.
        Validates state transition: CONFIRMED -> CHECKED_IN.
        Updates physical room status to OCCUPIED.
        """
        with transaction.atomic():
            res = Reservation.objects.select_for_update().get(id=reservation_id)
            if not res.can_check_in:
                raise ValidationError(f"Cannot check in reservation in status '{res.get_status_display()}'. Must be Confirmed.")

            old_status = res.status
            res.status = Reservation.Status.CHECKED_IN
            res.checked_in_at = timezone.now()
            res.save(update_fields=['status', 'checked_in_at', 'updated_at'])

            # Update room status to OCCUPIED
            room = Room.objects.select_for_update().get(id=res.room_id)
            old_room_status = room.status
            room.status = Room.Status.OCCUPIED
            room.save(update_fields=['status', 'updated_at'])

            # Write Audit Trail
            BookingAuditLog.objects.create(
                reservation=res,
                room=room,
                user=staff_user,
                action=BookingAuditLog.Action.CHECKED_IN,
                title=f"Guest Checked In: {res.guest_name}",
                details=f"Reservation {res.booking_reference} checked in by {staff_user.email}. Room {room.room_number} marked OCCUPIED.",
                ip_address=ip_address
            )
            return res

    @classmethod
    def check_out_guest(cls, reservation_id, staff_user, ip_address=''):
        """
        Staff action: Check out a departing guest.
        Validates state transition: CHECKED_IN -> CHECKED_OUT.
        Updates physical room status to DIRTY (needs housekeeping cleaning).
        """
        with transaction.atomic():
            res = Reservation.objects.select_for_update().get(id=reservation_id)
            if not res.can_check_out:
                raise ValidationError(f"Cannot check out reservation in status '{res.get_status_display()}'. Must be Checked In.")

            res.status = Reservation.Status.CHECKED_OUT
            res.checked_out_at = timezone.now()
            res.save(update_fields=['status', 'checked_out_at', 'updated_at'])

            # Update room status to DIRTY so housekeeping team is alerted
            room = Room.objects.select_for_update().get(id=res.room_id)
            room.status = Room.Status.DIRTY
            room.housekeeping_notes = "Checkout completed. Sanitization & fresh linens required."
            room.save(update_fields=['status', 'housekeeping_notes', 'updated_at'])

            # Write Audit Trail
            BookingAuditLog.objects.create(
                reservation=res,
                room=room,
                user=staff_user,
                action=BookingAuditLog.Action.CHECKED_OUT,
                title=f"Guest Checked Out: {res.guest_name}",
                details=f"Reservation {res.booking_reference} checked out by {staff_user.email}. Room {room.room_number} transitioned to DIRTY/CLEANING.",
                ip_address=ip_address
            )
            return res

    @classmethod
    def cancel_reservation(cls, reservation_id, user, reason="Guest requested cancellation", ip_address=''):
        """
        Cancels an active reservation.
        Validates state transition: CONFIRMED -> CANCELLED.
        Frees the room inventory immediately.
        """
        with transaction.atomic():
            res = Reservation.objects.select_for_update().get(id=reservation_id)
            if not res.can_cancel:
                raise ValidationError(f"Cannot cancel reservation in status '{res.get_status_display()}'.")

            res.status = Reservation.Status.CANCELLED
            res.payment_status = Reservation.PaymentStatus.REFUNDED
            res.cancelled_at = timezone.now()
            res.cancellation_reason = reason
            res.save(update_fields=['status', 'payment_status', 'cancelled_at', 'cancellation_reason', 'updated_at'])

            # If room was marked occupied, return to available
            room = Room.objects.select_for_update().get(id=res.room_id)
            if room.status == Room.Status.OCCUPIED:
                room.status = Room.Status.AVAILABLE
                room.save(update_fields=['status', 'updated_at'])

            # Write Audit Trail
            BookingAuditLog.objects.create(
                reservation=res,
                room=room,
                user=user,
                action=BookingAuditLog.Action.CANCELLED,
                title=f"Reservation {res.booking_reference} Cancelled",
                details=f"Cancelled by {user.email}. Reason: {reason}. Full sandbox refund processed.",
                ip_address=ip_address
            )
            return res
