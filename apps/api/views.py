import json
from datetime import datetime
from decimal import Decimal
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404, render
from django.db.models import Q
from apps.rooms.models import Room, RoomType
from apps.bookings.models import BookingHold, Reservation, BookingAuditLog
from apps.bookings.services import BookingService, BookingConflictError, InvalidDateRangeError
from apps.reports.services import ReportsService


def json_response(data, status=200):
    return JsonResponse(data, status=status, safe=isinstance(data, dict))


def json_error(message, status=400, details=None):
    payload = {'success': False, 'error': message}
    if details:
        payload['details'] = details
    return JsonResponse(payload, status=status)


def api_rooms_list(request):
    """GET /api/v1/rooms/ - Returns list of active room types."""
    room_types = RoomType.objects.filter(is_active=True).prefetch_related('amenities')
    data = []
    for rt in room_types:
        data.append({
            'id': rt.id,
            'name': rt.name,
            'slug': rt.slug,
            'tagline': rt.tagline,
            'description': rt.description,
            'base_price': str(rt.base_price),
            'weekend_price': str(rt.weekend_price) if rt.weekend_price else None,
            'max_guests': rt.max_guests,
            'bed_type': rt.bed_type,
            'size_sqft': rt.size_sqft,
            'image_url': rt.image_url,
            'amenities': [a.name for a in rt.amenities.all()],
            'total_rooms': rt.rooms.filter(is_active=True).count(),
        })
    return json_response({'success': True, 'count': len(data), 'room_types': data})


def api_availability(request):
    """GET /api/v1/availability/?check_in=YYYY-MM-DD&check_out=YYYY-MM-DD&guests=2"""
    check_in_str = request.GET.get('check_in')
    check_out_str = request.GET.get('check_out')
    guests_str = request.GET.get('guests', '1')

    if not check_in_str or not check_out_str:
        return json_error("Missing required query parameters: 'check_in' and 'check_out'.")

    try:
        check_in = datetime.strptime(check_in_str, '%Y-%m-%d').date()
        check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()
        guests = int(guests_str)

        rooms = BookingService.get_available_rooms(check_in, check_out, guests)
        results = []
        for r in rooms:
            pricing = BookingService.calculate_pricing(r.room_type, check_in, check_out, guests)
            results.append({
                'room_id': r.id,
                'room_number': r.room_number,
                'floor': r.floor,
                'room_type': {
                    'id': r.room_type.id,
                    'name': r.room_type.name,
                    'max_guests': r.room_type.max_guests,
                    'bed_type': r.room_type.bed_type,
                    'image_url': r.room_type.image_url,
                    'amenities': [a.name for a in r.room_type.amenities.all()[:4]],
                },
                'pricing': {
                    'num_nights': pricing['num_nights'],
                    'nightly_rate': str(pricing['average_nightly_rate']),
                    'room_subtotal': str(pricing['room_subtotal']),
                    'tax_amount': str(pricing['tax_amount']),
                    'service_fee': str(pricing['service_fee']),
                    'total_amount': str(pricing['total_amount']),
                }
            })
        return json_response({'success': True, 'available_rooms_count': len(results), 'rooms': results})

    except (ValueError, InvalidDateRangeError) as e:
        return json_error(str(e), status=400)
    except Exception as e:
        return json_error(f"Internal error: {str(e)}", status=500)


@csrf_exempt
def api_create_hold(request):
    """POST /api/v1/holds/ - Creates a 15-minute temporary hold."""
    if request.method != 'POST':
        return json_error("Method not allowed. Use POST.", status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        room_id = data.get('room_id')
        check_in = datetime.strptime(data.get('check_in'), '%Y-%m-%d').date()
        check_out = datetime.strptime(data.get('check_out'), '%Y-%m-%d').date()
        guests = int(data.get('guests', 1))

        hold = BookingService.create_hold(
            room_id=room_id,
            check_in=check_in,
            check_out=check_out,
            guests_count=guests,
            guest_user=request.user if request.user.is_authenticated else None,
            ip_address=request.META.get('REMOTE_ADDR', '')
        )

        return json_response({
            'success': True,
            'hold_id': str(hold.hold_id),
            'room_id': hold.room.id,
            'room_number': hold.room.room_number,
            'room_type': hold.room_type.name,
            'check_in': hold.check_in.isoformat(),
            'check_out': hold.check_out.isoformat(),
            'guests_count': hold.guests_count,
            'estimated_total': str(hold.estimated_total),
            'expires_at': hold.expires_at.isoformat(),
            'remaining_seconds': hold.remaining_seconds
        }, status=201)

    except (BookingConflictError, InvalidDateRangeError) as e:
        return json_error(str(e), status=409)
    except Exception as e:
        return json_error(f"Error creating hold: {str(e)}", status=400)


@csrf_exempt
def api_confirm_booking(request):
    """POST /api/v1/bookings/ - Confirms booking using hold_id."""
    if request.method != 'POST':
        return json_error("Method not allowed. Use POST.", status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        hold_id = data.get('hold_id')
        guest_name = data.get('guest_name', 'Guest')
        guest_email = data.get('guest_email', 'guest@example.com')
        guest_phone = data.get('guest_phone', '+1-555-0100')
        special_requests = data.get('special_requests', '')
        payment_method = data.get('payment_method', 'CARD_SANDBOX')

        # Link or create guest user
        guest_user = request.user
        if not guest_user.is_authenticated:
            from apps.accounts.models import User
            guest_user, _ = User.objects.get_or_create(
                email=guest_email,
                defaults={'username': guest_email.split('@')[0], 'first_name': guest_name, 'role': User.Role.GUEST}
            )

        reservation = BookingService.confirm_booking(
            hold_id=hold_id,
            guest_user=guest_user,
            guest_details={
                'name': guest_name,
                'email': guest_email,
                'phone': guest_phone,
                'special_requests': special_requests,
            },
            payment_data={
                'payment_method': payment_method,
                'has_breakfast': data.get('has_breakfast', False),
                'has_shuttle': data.get('has_shuttle', False),
            },
            ip_address=request.META.get('REMOTE_ADDR', '')
        )

        return json_response({
            'success': True,
            'booking_reference': reservation.booking_reference,
            'status': reservation.status,
            'guest_name': reservation.guest_name,
            'guest_email': reservation.guest_email,
            'room_number': reservation.room.room_number,
            'room_type': reservation.room_type.name,
            'check_in': reservation.check_in.isoformat(),
            'check_out': reservation.check_out.isoformat(),
            'num_nights': reservation.num_nights,
            'total_amount': str(reservation.total_amount),
            'transaction_id': reservation.transaction_id,
            'paid_at': reservation.paid_at.isoformat() if reservation.paid_at else None,
        }, status=201)

    except BookingConflictError as e:
        return json_error(str(e), status=409)
    except Exception as e:
        return json_error(f"Booking confirmation failed: {str(e)}", status=400)


def api_booking_detail(request, reference):
    """GET /api/v1/bookings/<reference>/"""
    res = get_object_or_404(Reservation.objects.select_related('room', 'room_type'), booking_reference=reference)
    return json_response({
        'success': True,
        'booking_reference': res.booking_reference,
        'guest_name': res.guest_name,
        'guest_email': res.guest_email,
        'guest_phone': res.guest_phone,
        'special_requests': res.special_requests,
        'room_number': res.room.room_number,
        'floor': res.room.floor,
        'room_type': res.room_type.name,
        'check_in': res.check_in.isoformat(),
        'check_out': res.check_out.isoformat(),
        'num_nights': res.num_nights,
        'guests_count': res.guests_count,
        'status': res.status,
        'payment_status': res.payment_status,
        'financials': {
            'nightly_rate': str(res.nightly_rate),
            'room_subtotal': str(res.room_subtotal),
            'tax_amount': str(res.tax_amount),
            'service_fee': str(res.service_fee),
            'addons_amount': str(res.addons_amount),
            'total_amount': str(res.total_amount),
        },
        'transaction_id': res.transaction_id,
        'created_at': res.created_at.isoformat(),
    })


@csrf_exempt
def api_cancel_booking(request, reference):
    """POST /api/v1/bookings/<reference>/cancel/"""
    if request.method != 'POST':
        return json_error("Method not allowed. Use POST.", status=405)

    res = get_object_or_404(Reservation, booking_reference=reference)
    user = request.user if request.user.is_authenticated else res.guest
    try:
        cancelled_res = BookingService.cancel_reservation(
            res.id,
            user=user,
            reason="Cancelled via React Portal",
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        return json_response({
            'success': True,
            'booking_reference': cancelled_res.booking_reference,
            'status': cancelled_res.status,
            'refund_status': cancelled_res.payment_status,
            'message': "Booking cancelled successfully and room returned to inventory."
        })
    except Exception as e:
        return json_error(str(e), status=400)


@csrf_exempt
def api_check_in(request, reference):
    """POST /api/v1/bookings/<reference>/check-in/"""
    if request.method != 'POST':
        return json_error("Method not allowed. Use POST.", status=405)

    res = get_object_or_404(Reservation, booking_reference=reference)
    user = request.user if request.user.is_authenticated else res.guest
    try:
        updated_res = BookingService.check_in_guest(
            res.id,
            staff_user=user,
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        return json_response({
            'success': True,
            'booking_reference': updated_res.booking_reference,
            'status': updated_res.status,
            'room_status': updated_res.room.status,
            'checked_in_at': updated_res.checked_in_at.isoformat()
        })
    except Exception as e:
        return json_error(str(e), status=400)


@csrf_exempt
def api_check_out(request, reference):
    """POST /api/v1/bookings/<reference>/check-out/"""
    if request.method != 'POST':
        return json_error("Method not allowed. Use POST.", status=405)

    res = get_object_or_404(Reservation, booking_reference=reference)
    user = request.user if request.user.is_authenticated else res.guest
    try:
        updated_res = BookingService.check_out_guest(
            res.id,
            staff_user=user,
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        return json_response({
            'success': True,
            'booking_reference': updated_res.booking_reference,
            'status': updated_res.status,
            'room_status': updated_res.room.status,
            'checked_out_at': updated_res.checked_out_at.isoformat()
        })
    except Exception as e:
        return json_error(str(e), status=400)


def api_reservations_list(request):
    """GET /api/v1/reservations/?email=...&status=...&q=..."""
    qs = Reservation.objects.select_related('room', 'room_type', 'guest').order_by('-check_in')
    
    email = request.GET.get('email')
    status = request.GET.get('status')
    q = request.GET.get('q')

    if email:
        qs = qs.filter(guest_email__iexact=email.strip())
    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(
            Q(booking_reference__icontains=q) |
            Q(guest_name__icontains=q) |
            Q(room__room_number__icontains=q) |
            Q(guest_email__icontains=q)
        )

    items = []
    for r in qs[:100]:
        items.append({
            'id': r.id,
            'booking_reference': r.booking_reference,
            'guest_name': r.guest_name,
            'guest_email': r.guest_email,
            'guest_phone': r.guest_phone,
            'special_requests': r.special_requests,
            'room_number': r.room.room_number,
            'floor': r.room.floor,
            'room_type': r.room_type.name,
            'image_url': r.room_type.image_url,
            'check_in': r.check_in.isoformat(),
            'check_out': r.check_out.isoformat(),
            'num_nights': r.num_nights,
            'guests_count': r.guests_count,
            'status': r.status,
            'total_amount': str(r.total_amount),
            'can_check_in': r.can_check_in,
            'can_check_out': r.can_check_out,
            'can_cancel': r.can_cancel,
        })
    return json_response({'success': True, 'count': len(items), 'reservations': items})


def api_inventory_list(request):
    """GET /api/v1/inventory/ - Returns all physical rooms with status & notes."""
    rooms = Room.objects.select_related('room_type').all().order_by('floor', 'room_number')
    items = []
    for r in rooms:
        items.append({
            'id': r.id,
            'room_number': r.room_number,
            'floor': r.floor,
            'status': r.status,
            'housekeeping_notes': r.housekeeping_notes,
            'room_type': {
                'id': r.room_type.id,
                'name': r.room_type.name,
                'base_price': str(r.room_type.base_price),
                'weekend_price': str(r.room_type.weekend_price) if r.room_type.weekend_price else None,
                'max_guests': r.room_type.max_guests,
                'bed_type': r.room_type.bed_type,
            }
        })
    return json_response({'success': True, 'count': len(items), 'rooms': items})


@csrf_exempt
def api_update_room_status(request, pk):
    """POST /api/v1/rooms/<id>/status/"""
    if request.method != 'POST':
        return json_error("Method not allowed. Use POST.", status=405)

    room = get_object_or_404(Room, pk=pk)
    try:
        data = json.loads(request.body.decode('utf-8'))
        new_status = data.get('status')
        notes = data.get('notes', room.housekeeping_notes)

        if new_status not in dict(Room.Status.choices):
            return json_error("Invalid status choice.")

        old_status = room.status
        room.status = new_status
        room.housekeeping_notes = notes
        room.save()

        BookingAuditLog.objects.create(
            room=room,
            user=request.user if request.user.is_authenticated else None,
            action=BookingAuditLog.Action.ROOM_STATUS_CHANGED,
            title=f"Room {room.room_number} status changed to {room.get_status_display()}",
            details=f"Status transitioned from {old_status} to {new_status} via React Console."
        )

        return json_response({
            'success': True,
            'room_number': room.room_number,
            'status': room.status,
            'housekeeping_notes': room.housekeeping_notes
        })
    except Exception as e:
        return json_error(str(e), status=400)


@csrf_exempt
def api_update_rate(request, pk):
    """POST /api/v1/rooms/types/<id>/rate/"""
    if request.method != 'POST':
        return json_error("Method not allowed. Use POST.", status=405)

    rt = get_object_or_404(RoomType, pk=pk)
    try:
        data = json.loads(request.body.decode('utf-8'))
        base_price = data.get('base_price')
        weekend_price = data.get('weekend_price')

        if base_price:
            rt.base_price = Decimal(str(base_price))
        if weekend_price:
            rt.weekend_price = Decimal(str(weekend_price))
        rt.save()

        BookingAuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action=BookingAuditLog.Action.RATE_UPDATED,
            title=f"Rate Updated: {rt.name}",
            details=f"New Weekday Base: ${rt.base_price}, Weekend: ${rt.weekend_price}"
        )

        return json_response({
            'success': True,
            'room_type_id': rt.id,
            'name': rt.name,
            'base_price': str(rt.base_price),
            'weekend_price': str(rt.weekend_price)
        })
    except Exception as e:
        return json_error(str(e), status=400)


def api_audit_logs(request):
    """GET /api/v1/audit/"""
    logs = BookingAuditLog.objects.select_related('reservation', 'room', 'user').order_by('-created_at')[:50]
    items = []
    for l in logs:
        items.append({
            'id': l.id,
            'action': l.action,
            'title': l.title,
            'details': l.details,
            'created_at': l.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'user': l.user.email if l.user else 'System',
            'room_number': l.room.room_number if l.room else None,
            'booking_reference': l.reservation.booking_reference if l.reservation else None,
        })
    return json_response({'success': True, 'count': len(items), 'logs': items})


def api_operations_report(request):
    """GET /api/v1/reports/operations/?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD"""
    start_str = request.GET.get('start_date')
    end_str = request.GET.get('end_date')

    try:
        start_date = datetime.strptime(start_str, '%Y-%m-%d').date() if start_str else datetime.today().date()
        end_date = datetime.strptime(end_str, '%Y-%m-%d').date() if end_str else start_date
        report = ReportsService.get_operations_report(start_date, end_date)
        return json_response({
            'success': True,
            'date_range': {'start': start_date.isoformat(), 'end': end_date.isoformat()},
            'num_days': report['num_days'],
            'occupancy_rate_pct': report['occupancy_rate'],
            'total_revenue': str(report['total_revenue']),
            'adr': str(report['adr']),
            'revpar': str(report['revpar']),
            'total_rooms': report['total_rooms'],
            'total_occupied_nights': report['total_occupied_room_nights'],
            'total_available_nights': report['total_room_nights_available'],
            'room_statuses': report['room_statuses'],
            'daily_breakdown': [
                {
                    'date': d['date'].isoformat(),
                    'date_str': d['date_str'],
                    'day_name': d['day_name'],
                    'occupied_rooms': d['occupied_rooms'],
                    'available_rooms': d['available_rooms'],
                    'occupancy_pct': d['occupancy_pct'],
                    'revenue': str(d['revenue']),
                }
                for d in report['daily_breakdown']
            ]
        })
    except Exception as e:
        return json_error(str(e), status=400)


def swagger_docs_view(request):
    """Interactive Swagger UI documentation page."""
    return render(request, 'api/swagger.html')


def openapi_spec_view(request):
    """OpenAPI 3.0 JSON specification."""
    # (Spec definition)
    from apps.api.openapi import get_openapi_spec
    return JsonResponse(get_openapi_spec())
