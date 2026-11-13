from datetime import date, datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.db import models
from apps.accounts.decorators import hotel_admin_required, hotel_staff_required
from apps.rooms.models import Room, RoomType, Amenity
from .models import BookingHold, Reservation, BookingAuditLog
from .services import BookingService, BookingConflictError, InvalidDateRangeError


def search_rooms(request):
    """
    Availability Search view:
    Validates check-in, check-out dates, guest counts, and finds operational rooms.
    Accounts for existing reservations and temporary holds.
    """
    today = timezone.localdate()
    default_check_in = today + timedelta(days=1)
    default_check_out = default_check_in + timedelta(days=2)

    check_in_str = request.GET.get('check_in', default_check_in.isoformat())
    check_out_str = request.GET.get('check_out', default_check_out.isoformat())
    guests_str = request.GET.get('guests', '2')
    room_type_id = request.GET.get('room_type', '')

    available_room_types = []
    error_message = None

    try:
        check_in = datetime.strptime(check_in_str, '%Y-%m-%d').date()
        check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()
        guests = max(1, int(guests_str))

        # Strict validation
        if check_in < today:
            raise InvalidDateRangeError("Check-in date cannot be in the past.")
        if check_out <= check_in:
            raise InvalidDateRangeError("Check-out date must be strictly after check-in date.")
        if (check_out - check_in).days > 90:
            raise InvalidDateRangeError("Maximum stay duration is 90 nights.")

        # Query available rooms
        available_rooms = BookingService.get_available_rooms(
            check_in=check_in,
            check_out=check_out,
            guests_count=guests,
            room_type_id=int(room_type_id) if room_type_id else None
        )

        # Group by room type with price calculation
        room_types = RoomType.objects.filter(is_active=True).prefetch_related('amenities')
        for rt in room_types:
            rt_rooms = [r for r in available_rooms if r.room_type_id == rt.id]
            if rt_rooms:
                pricing = BookingService.calculate_pricing(rt, check_in, check_out, guests)
                available_room_types.append({
                    'room_type': rt,
                    'available_count': len(rt_rooms),
                    'sample_room': rt_rooms[0],
                    'pricing': pricing,
                })

    except ValueError:
        error_message = "Invalid date or guest format provided."
    except InvalidDateRangeError as e:
        error_message = str(e)
    except Exception as e:
        error_message = f"Search error: {str(e)}"

    all_room_types = RoomType.objects.filter(is_active=True)

    context = {
        'check_in': check_in_str,
        'check_out': check_out_str,
        'guests': guests_str,
        'selected_room_type': room_type_id,
        'room_types': all_room_types,
        'results': available_room_types,
        'error_message': error_message,
        'today': today.isoformat(),
    }
    return render(request, 'bookings/search_results.html', context)


def room_detail(request, slug):
    """Detailed view for a specific Room Type with amenity showcase and booking widget."""
    room_type = get_object_or_404(RoomType.objects.prefetch_related('amenities'), slug=slug)
    today = timezone.localdate()
    default_check_in = today + timedelta(days=1)
    default_check_out = default_check_in + timedelta(days=2)

    pricing_preview = BookingService.calculate_pricing(room_type, default_check_in, default_check_out, guests_count=2)

    return render(request, 'bookings/room_detail.html', {
        'room_type': room_type,
        'default_check_in': default_check_in.isoformat(),
        'default_check_out': default_check_out.isoformat(),
        'pricing_preview': pricing_preview,
        'today': today.isoformat(),
    })


@login_required
def create_hold(request):
    """
    POST action: Creates a 15-minute temporary hold on a specific room,
    then redirects to the checkout / payment screen.
    """
    if request.method != 'POST':
        return redirect('bookings:search')

    room_id = request.POST.get('room_id')
    check_in_str = request.POST.get('check_in')
    check_out_str = request.POST.get('check_out')
    guests_str = request.POST.get('guests', '2')

    try:
        check_in = datetime.strptime(check_in_str, '%Y-%m-%d').date()
        check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()
        guests = int(guests_str)
        ip = request.META.get('REMOTE_ADDR', '')

        hold = BookingService.create_hold(
            room_id=room_id,
            check_in=check_in,
            check_out=check_out,
            guests_count=guests,
            guest_user=request.user,
            ip_address=ip
        )
        return redirect('bookings:checkout', hold_id=hold.hold_id)

    except (InvalidDateRangeError, BookingConflictError) as e:
        messages.error(request, str(e))
        return redirect('bookings:search')
    except Exception as e:
        messages.error(request, f"Unable to hold room: {str(e)}")
        return redirect('bookings:search')


@login_required
def checkout_view(request, hold_id):
    """
    Checkout screen: Displays the 15-minute hold timer, itemized pricing,
    guest details confirmation, and simulated payment credentials.
    """
    hold = get_object_or_404(BookingHold.objects.select_related('room', 'room_type'), hold_id=hold_id)

    if hold.is_consumed:
        messages.info(request, "This booking has already been confirmed.")
        try:
            res = Reservation.objects.get(room=hold.room, check_in=hold.check_in, check_out=hold.check_out)
            return redirect('bookings:confirmation', reference=res.booking_reference)
        except Reservation.DoesNotExist:
            return redirect('bookings:guest_bookings')

    if hold.is_expired:
        messages.error(request, "Your 15-minute hold has expired. Please select an available room.")
        return redirect('bookings:search')

    has_breakfast = request.POST.get('has_breakfast') == 'on' or request.GET.get('breakfast') == '1'
    has_shuttle = request.POST.get('has_shuttle') == 'on' or request.GET.get('shuttle') == '1'

    pricing = BookingService.calculate_pricing(
        hold.room_type,
        hold.check_in,
        hold.check_out,
        hold.guests_count,
        has_breakfast=has_breakfast,
        has_shuttle=has_shuttle
    )

    if request.method == 'POST' and 'confirm_payment' in request.POST:
        guest_details = {
            'name': request.POST.get('guest_name', request.user.get_full_name() or request.user.username),
            'email': request.POST.get('guest_email', request.user.email),
            'phone': request.POST.get('guest_phone', request.user.phone_number or ''),
            'special_requests': request.POST.get('special_requests', '').strip(),
        }
        payment_data = {
            'payment_method': request.POST.get('payment_method', 'CARD_SANDBOX'),
            'has_breakfast': has_breakfast,
            'has_shuttle': has_shuttle,
        }
        ip = request.META.get('REMOTE_ADDR', '')

        try:
            reservation = BookingService.confirm_booking(
                hold_id=hold.hold_id,
                guest_user=request.user,
                guest_details=guest_details,
                payment_data=payment_data,
                ip_address=ip
            )
            messages.success(request, f"Booking successfully confirmed! Reference: {reservation.booking_reference}")
            return redirect('bookings:confirmation', reference=reservation.booking_reference)

        except BookingConflictError as e:
            messages.error(request, str(e))
            return redirect('bookings:search')
        except Exception as e:
            messages.error(request, f"Payment processing error: {str(e)}")

    context = {
        'hold': hold,
        'pricing': pricing,
        'has_breakfast': has_breakfast,
        'has_shuttle': has_shuttle,
        'remaining_seconds': hold.remaining_seconds,
    }
    return render(request, 'bookings/checkout.html', context)


@login_required
def booking_confirmation(request, reference):
    """Presents the confirmed booking voucher, QR reference, and itemized receipt."""
    reservation = get_object_or_404(
        Reservation.objects.select_related('room', 'room_type', 'guest'),
        booking_reference=reference
    )
    # Check access permission: Guest owner, Staff, or Admin
    if not (request.user.is_hotel_staff or reservation.guest == request.user):
        messages.error(request, "You do not have permission to view this reservation.")
        return redirect('core:home')

    return render(request, 'bookings/confirmation.html', {'reservation': reservation})


@login_required
def guest_bookings_list(request):
    """Guest portal: View my active stays, upcoming reservations, and stay history."""
    reservations = Reservation.objects.filter(guest=request.user).select_related('room', 'room_type').order_by('-check_in')
    today = timezone.localdate()

    active_stays = reservations.filter(status=Reservation.Status.CHECKED_IN)
    upcoming_stays = reservations.filter(status=Reservation.Status.CONFIRMED, check_in__gte=today)
    past_stays = reservations.exclude(status__in=[Reservation.Status.CONFIRMED, Reservation.Status.CHECKED_IN])

    return render(request, 'bookings/guest_bookings.html', {
        'active_stays': active_stays,
        'upcoming_stays': upcoming_stays,
        'past_stays': past_stays,
    })


@login_required
def guest_cancel_booking(request, reference):
    """Guest action: Cancel a confirmed booking."""
    reservation = get_object_or_404(Reservation, booking_reference=reference)

    if not (request.user.is_hotel_staff or reservation.guest == request.user):
        messages.error(request, "Permission denied.")
        return redirect('bookings:guest_bookings')

    if request.method == 'POST':
        reason = request.POST.get('cancellation_reason', 'Cancelled by guest').strip()
        ip = request.META.get('REMOTE_ADDR', '')

        try:
            BookingService.cancel_reservation(reservation.id, request.user, reason=reason, ip_address=ip)
            messages.success(request, f"Reservation {reference} has been cancelled and full sandbox refund initiated.")
        except Exception as e:
            messages.error(request, f"Error cancelling reservation: {str(e)}")

    if request.user.is_hotel_staff:
        return redirect('bookings:staff_desk')
    return redirect('bookings:guest_bookings')


@hotel_staff_required
def staff_desk_view(request):
    """
    Staff / Front Desk Operations view:
    Shows arrivals, departures, in-house guests, and comprehensive search/filter.
    Enables 1-click Check-In and Check-Out.
    """
    today = timezone.localdate()
    tab = request.GET.get('tab', 'arrivals')
    search_query = request.GET.get('q', '').strip()

    base_qs = Reservation.objects.select_related('room', 'room_type', 'guest')

    if search_query:
        base_qs = base_qs.filter(
            models.Q(booking_reference__icontains=search_query) |
            models.Q(guest_name__icontains=search_query) |
            models.Q(guest_email__icontains=search_query) |
            models.Q(room__room_number__icontains=search_query)
        )

    arrivals = base_qs.filter(status=Reservation.Status.CONFIRMED, check_in=today)
    departures = base_qs.filter(status=Reservation.Status.CHECKED_IN, check_out=today)
    in_house = base_qs.filter(status=Reservation.Status.CHECKED_IN)
    all_bookings = base_qs.order_by('-check_in')[:50]

    context = {
        'today': today,
        'tab': tab,
        'search_query': search_query,
        'arrivals': arrivals,
        'departures': departures,
        'in_house': in_house,
        'all_bookings': all_bookings,
        'counts': {
            'arrivals': arrivals.count(),
            'departures': departures.count(),
            'in_house': in_house.count(),
        }
    }
    return render(request, 'bookings/staff_desk.html', context)


@hotel_staff_required
def staff_check_in(request, reference):
    """Staff action: Process physical guest check-in."""
    reservation = get_object_or_404(Reservation, booking_reference=reference)
    if request.method == 'POST':
        ip = request.META.get('REMOTE_ADDR', '')
        try:
            BookingService.check_in_guest(reservation.id, request.user, ip_address=ip)
            messages.success(request, f"Guest {reservation.guest_name} successfully checked into Room {reservation.room.room_number}.")
        except Exception as e:
            messages.error(request, f"Check-in error: {str(e)}")
    return redirect('bookings:staff_desk')


@hotel_staff_required
def staff_check_out(request, reference):
    """Staff action: Process guest checkout and room release."""
    reservation = get_object_or_404(Reservation, booking_reference=reference)
    if request.method == 'POST':
        ip = request.META.get('REMOTE_ADDR', '')
        try:
            BookingService.check_out_guest(reservation.id, request.user, ip_address=ip)
            messages.success(request, f"Guest {reservation.guest_name} checked out. Room {reservation.room.room_number} marked for housekeeping.")
        except Exception as e:
            messages.error(request, f"Checkout error: {str(e)}")
    return redirect('bookings:staff_desk')


@hotel_admin_required
def audit_trail_view(request):
    """Admin view: Full immutable audit trail of operational events."""
    action_filter = request.GET.get('action')
    logs = BookingAuditLog.objects.select_related('reservation', 'room', 'user')

    if action_filter:
        logs = logs.filter(action=action_filter)

    paginator = Paginator(logs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'bookings/audit_trail.html', {
        'page_obj': page_obj,
        'actions': BookingAuditLog.Action.choices,
        'selected_action': action_filter,
    })
