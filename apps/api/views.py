import json
from datetime import datetime
from decimal import Decimal
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404, render
from apps.rooms.models import Room, RoomType
from apps.bookings.models import BookingHold, Reservation
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
            'base_price': str(rt.base_price),
            'weekend_price': str(rt.weekend_price) if rt.weekend_price else None,
            'max_guests': rt.max_guests,
            'bed_type': rt.bed_type,
            'size_sqft': rt.size_sqft,
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
            'room_number': hold.room.room_number,
            'room_type': hold.room_type.name,
            'check_in': hold.check_in.isoformat(),
            'check_out': hold.check_out.isoformat(),
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

        # Fallback guest user if anonymous
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
            'room_number': reservation.room.room_number,
            'room_type': reservation.room_type.name,
            'check_in': reservation.check_in.isoformat(),
            'check_out': reservation.check_out.isoformat(),
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
        'room_number': res.room.room_number,
        'room_type': res.room_type.name,
        'check_in': res.check_in.isoformat(),
        'check_out': res.check_out.isoformat(),
        'num_nights': res.num_nights,
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
            reason="Cancelled via REST API",
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
            'occupancy_rate_pct': report['occupancy_rate'],
            'total_revenue': str(report['total_revenue']),
            'adr': str(report['adr']),
            'revpar': str(report['revpar']),
            'total_rooms': report['total_rooms'],
            'room_statuses': report['room_statuses'],
        })
    except Exception as e:
        return json_error(str(e), status=400)


def swagger_docs_view(request):
    """Interactive Swagger UI documentation page."""
    return render(request, 'api/swagger.html')


def openapi_spec_view(request):
    """OpenAPI 3.0 JSON specification."""
    spec = {
        "openapi": "3.0.3",
        "info": {
            "title": "GrandView Hotel Management & Reservation API",
            "version": "1.0.0",
            "description": "Production REST API for room inventory, availability checks, 15-minute temporary holds, concurrent booking processing, front-desk check-in/out, and operations reports."
        },
        "servers": [{"url": "http://127.0.0.1:8000"}],
        "paths": {
            "/api/v1/rooms/": {
                "get": {
                    "summary": "List all active room types",
                    "responses": {"200": {"description": "List of room types with rates and capacity"}}
                }
            },
            "/api/v1/availability/": {
                "get": {
                    "summary": "Query room availability for date range",
                    "parameters": [
                        {"name": "check_in", "in": "query", "required": True, "schema": {"type": "string", "format": "date"}},
                        {"name": "check_out", "in": "query", "required": True, "schema": {"type": "string", "format": "date"}},
                        {"name": "guests", "in": "query", "required": False, "schema": {"type": "integer"}}
                    ],
                    "responses": {"200": {"description": "Available rooms and pricing breakdown"}}
                }
            },
            "/api/v1/holds/": {
                "post": {
                    "summary": "Place a 15-minute temporary hold on a room",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {
                            "type": "object",
                            "properties": {
                                "room_id": {"type": "integer"},
                                "check_in": {"type": "string", "format": "date"},
                                "check_out": {"type": "string", "format": "date"},
                                "guests": {"type": "integer"}
                            }
                        }}}
                    },
                    "responses": {
                        "201": {"description": "Hold created successfully"},
                        "409": {"description": "Room already reserved or held"}
                    }
                }
            },
            "/api/v1/bookings/": {
                "post": {
                    "summary": "Confirm reservation using hold token and simulated payment",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {
                            "type": "object",
                            "properties": {
                                "hold_id": {"type": "string", "format": "uuid"},
                                "guest_name": {"type": "string"},
                                "guest_email": {"type": "string", "format": "email"},
                                "guest_phone": {"type": "string"},
                                "payment_method": {"type": "string"}
                            }
                        }}}
                    },
                    "responses": {
                        "201": {"description": "Reservation confirmed and guaranteed"},
                        "409": {"description": "Concurrency or hold expiry error"}
                    }
                }
            },
            "/api/v1/bookings/{reference}/": {
                "get": {
                    "summary": "Retrieve booking voucher details",
                    "parameters": [{"name": "reference", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "Reservation details and financials"}}
                }
            },
            "/api/v1/bookings/{reference}/cancel/": {
                "post": {
                    "summary": "Cancel booking and release inventory",
                    "parameters": [{"name": "reference", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "Cancelled and refunded"}}
                }
            },
            "/api/v1/bookings/{reference}/check-in/": {
                "post": {
                    "summary": "Front desk check-in action",
                    "parameters": [{"name": "reference", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "Guest checked in, room marked OCCUPIED"}}
                }
            },
            "/api/v1/bookings/{reference}/check-out/": {
                "post": {
                    "summary": "Front desk check-out action",
                    "parameters": [{"name": "reference", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "Guest checked out, room marked DIRTY/CLEANING"}}
                }
            },
            "/api/v1/reports/operations/": {
                "get": {
                    "summary": "Retrieve occupancy rate, revenue, ADR, and RevPAR",
                    "parameters": [
                        {"name": "start_date", "in": "query", "required": False, "schema": {"type": "string", "format": "date"}},
                        {"name": "end_date", "in": "query", "required": False, "schema": {"type": "string", "format": "date"}}
                    ],
                    "responses": {"200": {"description": "Aggregated operations report"}}
                }
            }
        }
    }
    return JsonResponse(spec)
