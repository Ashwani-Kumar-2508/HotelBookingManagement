from datetime import date, timedelta, datetime
from decimal import Decimal
from django.db.models import Sum, Count, Q
from apps.rooms.models import Room, RoomType
from apps.bookings.models import Reservation


class ReportsService:
    @staticmethod
    def get_operations_report(start_date, end_date):
        """
        Computes accurate operational metrics for a selected date window:
        - Occupancy rate %
        - Total room nights available
        - Total room nights occupied
        - Gross Revenue, ADR (Average Daily Rate), and RevPAR
        - Daily breakdown
        - Housekeeping status breakdown
        """
        if end_date < start_date:
            end_date = start_date

        num_days = (end_date - start_date).days + 1
        total_rooms = Room.objects.filter(is_active=True).count()
        total_room_nights_available = total_rooms * num_days

        # Query reservations that overlap the date range and are valid stays
        overlapping_stays = Reservation.objects.filter(
            status__in=[Reservation.Status.CONFIRMED, Reservation.Status.CHECKED_IN, Reservation.Status.CHECKED_OUT],
            check_in__lte=end_date,
            check_out__gte=start_date
        ).select_related('room', 'room_type')

        # Day-by-day calculation
        daily_breakdown = []
        total_occupied_room_nights = 0
        total_period_revenue = Decimal('0.00')

        curr = start_date
        while curr <= end_date:
            # Active stays on date curr (guests staying overnight)
            active_on_day = [
                res for res in overlapping_stays 
                if res.check_in <= curr < res.check_out
            ]
            occupied_count = len(active_on_day)
            total_occupied_room_nights += occupied_count

            # Daily revenue estimate
            day_rev = sum(res.nightly_rate for res in active_on_day)
            total_period_revenue += day_rev

            daily_occupancy_pct = (occupied_count / total_rooms * 100) if total_rooms > 0 else 0

            daily_breakdown.append({
                'date': curr,
                'date_str': curr.strftime('%b %d, %Y'),
                'day_name': curr.strftime('%a'),
                'occupied_rooms': occupied_count,
                'available_rooms': max(0, total_rooms - occupied_count),
                'occupancy_pct': round(daily_occupancy_pct, 1),
                'revenue': day_rev,
            })
            curr += timedelta(days=1)

        # Period aggregates
        occupancy_rate = (
            (total_occupied_room_nights / total_room_nights_available * 100)
            if total_room_nights_available > 0 else 0.0
        )

        adr = (
            (total_period_revenue / total_occupied_room_nights)
            if total_occupied_room_nights > 0 else Decimal('0.00')
        )

        revpar = (
            (total_period_revenue / total_room_nights_available)
            if total_room_nights_available > 0 else Decimal('0.00')
        )

        # Reservations created within or checking in
        new_reservations_count = Reservation.objects.filter(
            check_in__range=[start_date, end_date]
        ).exclude(status=Reservation.Status.CANCELLED).count()

        cancellations_count = Reservation.objects.filter(
            status=Reservation.Status.CANCELLED,
            check_in__range=[start_date, end_date]
        ).count()

        # Current physical room inventory distribution
        room_statuses = {
            'AVAILABLE': Room.objects.filter(status=Room.Status.AVAILABLE, is_active=True).count(),
            'OCCUPIED': Room.objects.filter(status=Room.Status.OCCUPIED, is_active=True).count(),
            'DIRTY': Room.objects.filter(status=Room.Status.DIRTY, is_active=True).count(),
            'MAINTENANCE': Room.objects.filter(status=Room.Status.MAINTENANCE, is_active=True).count(),
        }

        # Upcoming arrivals and departures
        arrivals = Reservation.objects.filter(
            status=Reservation.Status.CONFIRMED,
            check_in__range=[start_date, end_date]
        ).select_related('room', 'room_type').order_by('check_in')

        departures = Reservation.objects.filter(
            status=Reservation.Status.CHECKED_IN,
            check_out__range=[start_date, end_date]
        ).select_related('room', 'room_type').order_by('check_out')

        return {
            'start_date': start_date,
            'end_date': end_date,
            'num_days': num_days,
            'total_rooms': total_rooms,
            'total_room_nights_available': total_room_nights_available,
            'total_occupied_room_nights': total_occupied_room_nights,
            'occupancy_rate': round(occupancy_rate, 1),
            'total_revenue': total_period_revenue.quantize(Decimal('0.01')),
            'adr': adr.quantize(Decimal('0.01')),
            'revpar': revpar.quantize(Decimal('0.01')),
            'new_reservations_count': new_reservations_count,
            'cancellations_count': cancellations_count,
            'daily_breakdown': daily_breakdown,
            'room_statuses': room_statuses,
            'arrivals': arrivals,
            'departures': departures,
        }
