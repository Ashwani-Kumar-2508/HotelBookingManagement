from datetime import datetime, timedelta
from django.shortcuts import render
from django.utils import timezone
from apps.accounts.decorators import hotel_admin_required, hotel_staff_required
from apps.rooms.models import Room
from .services import ReportsService


@hotel_admin_required
def dashboard_view(request):
    """
    Operations & Revenue Reporting Dashboard:
    Provides date-range filtering, occupancy rates, ADR, RevPAR,
    financial performance, and operational KPIs.
    """
    today = timezone.localdate()
    preset = request.GET.get('preset', '7days')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = today
            end_date = today + timedelta(days=6)
    else:
        if preset == 'today':
            start_date = today
            end_date = today
        elif preset == '30days':
            start_date = today - timedelta(days=15)
            end_date = today + timedelta(days=14)
        elif preset == 'this_month':
            start_date = today.replace(day=1)
            # End of current month
            next_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
            end_date = next_month - timedelta(days=1)
        else:  # default '7days'
            start_date = today
            end_date = today + timedelta(days=6)

    report = ReportsService.get_operations_report(start_date, end_date)

    context = {
        'report': report,
        'today': today,
        'preset': preset,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
    }
    return render(request, 'reports/dashboard.html', context)


@hotel_staff_required
def housekeeping_board(request):
    """
    Staff Housekeeping & Room Status Board:
    Provides real-time room status breakdown by floor with 1-click status actions.
    """
    rooms = Room.objects.select_related('room_type').all().order_by('floor', 'room_number')
    floors = sorted(list(set(rooms.values_list('floor', flat=True))))
    
    rooms_by_floor = {}
    for fl in floors:
        rooms_by_floor[fl] = [r for r in rooms if r.floor == fl]

    counts = {
        'total': rooms.count(),
        'available': rooms.filter(status=Room.Status.AVAILABLE).count(),
        'occupied': rooms.filter(status=Room.Status.OCCUPIED).count(),
        'dirty': rooms.filter(status=Room.Status.DIRTY).count(),
        'maintenance': rooms.filter(status=Room.Status.MAINTENANCE).count(),
    }

    return render(request, 'reports/housekeeping_board.html', {
        'rooms_by_floor': rooms_by_floor,
        'floors': floors,
        'counts': counts,
        'statuses': Room.Status.choices,
    })
