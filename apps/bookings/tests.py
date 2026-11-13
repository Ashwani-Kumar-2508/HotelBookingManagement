from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase, Client
from django.utils import timezone
from django.urls import reverse
from django.core.exceptions import PermissionDenied, ValidationError
from apps.accounts.models import User
from apps.rooms.models import Amenity, RoomType, Room
from apps.bookings.models import BookingHold, Reservation, BookingAuditLog
from apps.bookings.services import (
    BookingService, BookingConflictError, InvalidDateRangeError
)
from apps.reports.services import ReportsService


class HotelBookingTestCase(TestCase):
    def setUp(self):
        # Create users for all 3 RBAC roles
        self.admin_user = User.objects.create_superuser(
            username='admin_test',
            email='admin@grandview.com',
            password='password123',
            role=User.Role.ADMIN
        )
        self.staff_user = User.objects.create_user(
            username='staff_test',
            email='staff@grandview.com',
            password='password123',
            role=User.Role.STAFF
        )
        self.guest_user1 = User.objects.create_user(
            username='guest1_test',
            email='guest1@example.com',
            password='password123',
            first_name='David',
            last_name='Miller',
            role=User.Role.GUEST
        )
        self.guest_user2 = User.objects.create_user(
            username='guest2_test',
            email='guest2@example.com',
            password='password123',
            first_name='Sarah',
            last_name='Jenkins',
            role=User.Role.GUEST
        )

        # Create amenities & room types
        self.wifi = Amenity.objects.create(name='High-Speed Wi-Fi', icon='wifi')
        self.ocean_view = Amenity.objects.create(name='Ocean View', icon='eye')

        self.deluxe_type = RoomType.objects.create(
            name='Deluxe King Suite',
            slug='deluxe-king-suite',
            description='Ocean view king suite with luxury balcony.',
            base_price=Decimal('200.00'),
            weekend_price=Decimal('240.00'),
            max_guests=2,
            bed_type='1 King Bed',
            size_sqft=550
        )
        self.deluxe_type.amenities.add(self.wifi, self.ocean_view)

        # Create physical rooms
        self.room_101 = Room.objects.create(
            room_number='101',
            room_type=self.deluxe_type,
            floor=1,
            status=Room.Status.AVAILABLE
        )
        self.room_102 = Room.objects.create(
            room_number='102',
            room_type=self.deluxe_type,
            floor=1,
            status=Room.Status.AVAILABLE
        )

        self.today = timezone.localdate()
        self.check_in = self.today + timedelta(days=2)
        self.check_out = self.check_in + timedelta(days=3)  # 3 nights

    # =========================================================================
    # Acceptance Test 1: Search and Successful End-to-End Booking
    # =========================================================================
    def test_guest_search_and_successful_booking(self):
        """A guest can search availability, place a hold, and confirm a booking."""
        available = BookingService.get_available_rooms(self.check_in, self.check_out, guests_count=2)
        self.assertIn(self.room_101, available)
        self.assertIn(self.room_102, available)

        # 1. Place temporary hold
        hold = BookingService.create_hold(
            room_id=self.room_101.id,
            check_in=self.check_in,
            check_out=self.check_out,
            guests_count=2,
            guest_user=self.guest_user1
        )
        self.assertTrue(hold.is_active)
        self.assertFalse(hold.is_expired)

        # 2. Confirm reservation with itemized breakdown
        reservation = BookingService.confirm_booking(
            hold_id=hold.hold_id,
            guest_user=self.guest_user1,
            guest_details={
                'name': 'David Miller',
                'email': 'guest1@example.com',
                'phone': '+1 (555) 0199',
            },
            payment_data={
                'payment_method': 'CARD_SANDBOX',
                'has_breakfast': True,
                'has_shuttle': False,
            }
        )

        self.assertEqual(reservation.status, Reservation.Status.CONFIRMED)
        self.assertEqual(reservation.room, self.room_101)
        self.assertEqual(reservation.num_nights, 3)
        self.assertTrue(reservation.booking_reference.startswith('GV-'))
        self.assertTrue(reservation.total_amount > Decimal('0.00'))

        # Verify hold is consumed
        hold.refresh_from_db()
        self.assertTrue(hold.is_consumed)

        # Verify room 101 is now blocked, but room 102 remains available
        remaining_available = BookingService.get_available_rooms(self.check_in, self.check_out, guests_count=2)
        self.assertNotIn(self.room_101, remaining_available)
        self.assertIn(self.room_102, remaining_available)

    # =========================================================================
    # Acceptance Test 2: Concurrency & Overlap Prevention
    # =========================================================================
    def test_overlapping_booking_rejection(self):
        """A second request cannot confirm an overlapping booking for the same room."""
        # First confirmed booking for Room 101: Days 2 to 5
        hold1 = BookingService.create_hold(
            room_id=self.room_101.id,
            check_in=self.check_in,
            check_out=self.check_out,
            guests_count=2,
            guest_user=self.guest_user1
        )
        res1 = BookingService.confirm_booking(
            hold_id=hold1.hold_id,
            guest_user=self.guest_user1,
            guest_details={'name': 'David Miller', 'email': 'guest1@example.com', 'phone': '123'}
        )
        self.assertEqual(res1.status, Reservation.Status.CONFIRMED)

        # Second user attempts overlapping hold for Room 101 (Days 3 to 6 - overlaps by 2 nights)
        overlapping_check_in = self.check_in + timedelta(days=1)
        overlapping_check_out = self.check_out + timedelta(days=1)

        with self.assertRaises(BookingConflictError):
            BookingService.create_hold(
                room_id=self.room_101.id,
                check_in=overlapping_check_in,
                check_out=overlapping_check_out,
                guests_count=2,
                guest_user=self.guest_user2
            )

    # =========================================================================
    # Acceptance Test 3: Invalid Dates Validation
    # =========================================================================
    def test_invalid_dates_handling(self):
        """Check-out date <= check-in date or past dates must be strictly rejected."""
        # 1. Check-out date before check-in date
        with self.assertRaises(InvalidDateRangeError):
            BookingService.calculate_pricing(
                self.deluxe_type,
                check_in=self.today + timedelta(days=5),
                check_out=self.today + timedelta(days=2)
            )

        # 2. Check-out date same as check-in date (0 nights)
        with self.assertRaises(InvalidDateRangeError):
            BookingService.calculate_pricing(
                self.deluxe_type,
                check_in=self.today + timedelta(days=5),
                check_out=self.today + timedelta(days=5)
            )

        # 3. Stay exceeds 90 nights
        with self.assertRaises(InvalidDateRangeError):
            BookingService.calculate_pricing(
                self.deluxe_type,
                check_in=self.today,
                check_out=self.today + timedelta(days=100)
            )

    # =========================================================================
    # Acceptance Test 4: Expired Holds Do Not Block Inventory
    # =========================================================================
    def test_expired_holds_do_not_block_inventory(self):
        """Expired holds must automatically release room inventory."""
        past_time = timezone.now() - timedelta(minutes=20)
        
        # Create an expired hold
        expired_hold = BookingHold.objects.create(
            room=self.room_101,
            room_type=self.deluxe_type,
            guest=self.guest_user1,
            check_in=self.check_in,
            check_out=self.check_out,
            guests_count=2,
            expires_at=past_time,
            is_consumed=False
        )
        self.assertTrue(expired_hold.is_expired)

        # The room must STILL be available because the hold has expired
        available = BookingService.get_available_rooms(self.check_in, self.check_out, guests_count=2)
        self.assertIn(self.room_101, available)

        # Trying to confirm with the expired hold must fail
        with self.assertRaises(BookingConflictError):
            BookingService.confirm_booking(
                hold_id=expired_hold.hold_id,
                guest_user=self.guest_user1,
                guest_details={'name': 'David', 'email': 'd@example.com', 'phone': '123'}
            )

    # =========================================================================
    # Acceptance Test 5: Cancelled Bookings Release Inventory
    # =========================================================================
    def test_cancellation_releases_inventory(self):
        """A cancelled reservation restores the room to public availability."""
        hold = BookingService.create_hold(
            room_id=self.room_101.id,
            check_in=self.check_in,
            check_out=self.check_out,
            guests_count=2,
            guest_user=self.guest_user1
        )
        res = BookingService.confirm_booking(
            hold_id=hold.hold_id,
            guest_user=self.guest_user1,
            guest_details={'name': 'David', 'email': 'd@example.com', 'phone': '123'}
        )

        # Room is unavailable
        available_before = BookingService.get_available_rooms(self.check_in, self.check_out, guests_count=2)
        self.assertNotIn(self.room_101, available_before)

        # Cancel reservation
        cancelled_res = BookingService.cancel_reservation(res.id, user=self.guest_user1, reason="Travel delay")
        self.assertEqual(cancelled_res.status, Reservation.Status.CANCELLED)
        self.assertEqual(cancelled_res.payment_status, Reservation.PaymentStatus.REFUNDED)

        # Room is now available again!
        available_after = BookingService.get_available_rooms(self.check_in, self.check_out, guests_count=2)
        self.assertIn(self.room_101, available_after)

    # =========================================================================
    # Acceptance Test 6: Staff Check-In & Check-Out Lifecycle
    # =========================================================================
    def test_staff_check_in_and_check_out_lifecycle(self):
        """Staff can check in and check out guests, transitioning room status accurately."""
        hold = BookingService.create_hold(
            room_id=self.room_101.id,
            check_in=self.check_in,
            check_out=self.check_out,
            guests_count=2,
            guest_user=self.guest_user1
        )
        res = BookingService.confirm_booking(
            hold_id=hold.hold_id,
            guest_user=self.guest_user1,
            guest_details={'name': 'David', 'email': 'd@example.com', 'phone': '123'}
        )

        # 1. Staff Check-In
        checked_in_res = BookingService.check_in_guest(res.id, staff_user=self.staff_user)
        self.assertEqual(checked_in_res.status, Reservation.Status.CHECKED_IN)
        self.room_101.refresh_from_db()
        self.assertEqual(self.room_101.status, Room.Status.OCCUPIED)

        # Verify audit log recorded
        last_audit = BookingAuditLog.objects.filter(reservation=res).latest('created_at')
        self.assertEqual(last_audit.action, BookingAuditLog.Action.CHECKED_IN)

        # 2. Staff Check-Out
        checked_out_res = BookingService.check_out_guest(res.id, staff_user=self.staff_user)
        self.assertEqual(checked_out_res.status, Reservation.Status.CHECKED_OUT)
        self.room_101.refresh_from_db()
        self.assertEqual(self.room_101.status, Room.Status.DIRTY)  # marked for cleaning!

        # 3. Invalid transition test: cannot check in an already checked-out reservation
        with self.assertRaises(ValidationError):
            BookingService.check_in_guest(res.id, staff_user=self.staff_user)

    # =========================================================================
    # Acceptance Test 7: Operations Report Matches Underlying Reservation Data
    # =========================================================================
    def test_operations_report_matches_reservations(self):
        """Admin operations report metrics match reservation database figures."""
        # Create a confirmed booking for Room 101 for tomorrow (2 nights)
        start = self.today + timedelta(days=1)
        end = start + timedelta(days=2)
        pricing = BookingService.calculate_pricing(self.deluxe_type, start, end, guests_count=2)

        res = Reservation.objects.create(
            booking_reference="GV-2026-TEST",
            guest=self.guest_user1,
            guest_name="Test Guest",
            guest_email="test@example.com",
            guest_phone="555-0100",
            room=self.room_101,
            room_type=self.deluxe_type,
            check_in=start,
            check_out=end,
            guests_count=2,
            status=Reservation.Status.CONFIRMED,
            nightly_rate=pricing['average_nightly_rate'],
            num_nights=pricing['num_nights'],
            room_subtotal=pricing['room_subtotal'],
            tax_amount=pricing['tax_amount'],
            service_fee=pricing['service_fee'],
            addons_amount=pricing['addons_total'],
            total_amount=pricing['total_amount'],
            payment_status=Reservation.PaymentStatus.PAID
        )

        # Query report for this 2-day period
        report = ReportsService.get_operations_report(start, end - timedelta(days=1))
        
        # Room 101 occupied for 2 nights out of 2 total rooms * 2 days = 4 room nights available
        # Occupancy = (2 / 4) * 100 = 50.0%
        self.assertEqual(report['total_rooms'], 2)
        self.assertEqual(report['total_occupied_room_nights'], 2)
        self.assertEqual(report['total_room_nights_available'], 4)
        self.assertEqual(report['occupancy_rate'], 50.0)
        self.assertEqual(report['total_revenue'], pricing['room_subtotal'])

    # =========================================================================
    # Acceptance Test 8: RBAC Server-Side Authorization Security
    # =========================================================================
    def test_server_side_rbac_enforcement(self):
        """Unauthorized roles must be denied access with HTTP 403 / PermissionDenied."""
        client = Client()

        # 1. Unauthenticated user redirected to login
        response = client.get(reverse('reports:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

        # 2. Guest user cannot access Admin Reports (403 Forbidden)
        client.force_login(self.guest_user1)
        response_admin_rep = client.get(reverse('reports:dashboard'))
        self.assertEqual(response_admin_rep.status_code, 403)

        # 3. Guest user cannot access Front Desk Console (403 Forbidden)
        response_staff_desk = client.get(reverse('bookings:staff_desk'))
        self.assertEqual(response_staff_desk.status_code, 403)

        # 4. Front Desk Staff CAN access Front Desk Console (200 OK)
        client.force_login(self.staff_user)
        response_staff = client.get(reverse('bookings:staff_desk'))
        self.assertEqual(response_staff.status_code, 200)

        # 5. Front Desk Staff CANNOT access Admin-Only Room Type Creation (403 Forbidden)
        response_rt_create = client.get(reverse('rooms:room_type_create'))
        self.assertEqual(response_rt_create.status_code, 403)

        # 6. Admin CAN access Admin Reports & Room Type Creation (200 OK)
        client.force_login(self.admin_user)
        response_admin = client.get(reverse('reports:dashboard'))
        self.assertEqual(response_admin.status_code, 200)

    # =========================================================================
    # Acceptance Test 9: RESTful API Endpoints
    # =========================================================================
    def test_rest_api_availability_and_booking_journey(self):
        """Tests availability, hold creation, and booking confirmation via JSON API."""
        client = Client()

        # 1. Query availability
        avail_url = f"{reverse('api:availability')}?check_in={self.check_in}&check_out={self.check_out}&guests=2"
        res_avail = client.get(avail_url)
        self.assertEqual(res_avail.status_code, 200)
        data = res_avail.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['available_rooms_count'] >= 2)

        # 2. Place hold via API
        hold_payload = {
            'room_id': self.room_101.id,
            'check_in': self.check_in.isoformat(),
            'check_out': self.check_out.isoformat(),
            'guests': 2
        }
        res_hold = client.post(
            reverse('api:create_hold'),
            data=hold_payload,
            content_type='application/json'
        )
        self.assertEqual(res_hold.status_code, 201)
        hold_data = res_hold.json()
        self.assertTrue(hold_data['success'])
        hold_id = hold_data['hold_id']

        # 3. Confirm booking via API
        booking_payload = {
            'hold_id': hold_id,
            'guest_name': 'REST API Guest',
            'guest_email': 'api_guest@example.com',
            'guest_phone': '+1 (555) 9988',
            'payment_method': 'CARD_SANDBOX'
        }
        res_book = client.post(
            reverse('api:confirm_booking'),
            data=booking_payload,
            content_type='application/json'
        )
        self.assertEqual(res_book.status_code, 201)
        book_data = res_book.json()
        self.assertTrue(book_data['success'])
        ref = book_data['booking_reference']
        self.assertTrue(ref.startswith('GV-'))

        # 4. Conflict test: Overlapping hold on Room 101 returns 409
        res_conflict = client.post(
            reverse('api:create_hold'),
            data=hold_payload,
            content_type='application/json'
        )
        self.assertEqual(res_conflict.status_code, 409)
