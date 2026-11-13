from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.accounts.models import User
from apps.rooms.models import Amenity, RoomType, Room
from apps.bookings.models import BookingHold, Reservation, BookingAuditLog
from apps.bookings.services import BookingService


class Command(BaseCommand):
    help = 'Seeds database with realistic hotel rooms, rates, amenities, demo accounts, active reservations, and audit trail.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Clearing existing domain records..."))
        BookingAuditLog.objects.all().delete()
        Reservation.objects.all().delete()
        BookingHold.objects.all().delete()
        Room.objects.all().delete()
        RoomType.objects.all().delete()
        Amenity.objects.all().delete()
        User.objects.filter(email__in=[
            'admin@grandview.com', 'staff@grandview.com', 'guest@example.com', 'sarah@example.com'
        ]).delete()

        self.stdout.write(self.style.NOTICE("Creating Demo User Accounts with 1-Click Role Login..."))
        admin_user = User.objects.create_superuser(
            username='admin_hotel',
            email='admin@grandview.com',
            password='adminpassword123',
            first_name='Alexandre',
            last_name='Vanderbilt',
            phone_number='+1 (800) 555-0199',
            role=User.Role.ADMIN,
            department='Executive Management'
        )

        staff_user = User.objects.create_user(
            username='staff_frontdesk',
            email='staff@grandview.com',
            password='staffpassword123',
            first_name='Elena',
            last_name='Rostova',
            phone_number='+1 (800) 555-0144',
            role=User.Role.STAFF,
            department='Front Desk Operations'
        )

        guest_user = User.objects.create_user(
            username='guest_david',
            email='guest@example.com',
            password='guestpassword123',
            first_name='David',
            last_name='Miller',
            phone_number='+1 (415) 882-9901',
            role=User.Role.GUEST,
            vip_status=True
        )

        guest2_user = User.objects.create_user(
            username='guest_sarah',
            email='sarah@example.com',
            password='guestpassword123',
            first_name='Sarah',
            last_name='Jenkins',
            phone_number='+1 (212) 674-3312',
            role=User.Role.GUEST
        )

        self.stdout.write(self.style.SUCCESS("Demo accounts created successfully."))

        # 2. Amenities
        self.stdout.write(self.style.NOTICE("Creating Luxury Hotel Amenities..."))
        amenities_data = [
            ("Panoramic Ocean View", "eye", Amenity.Category.VIEW, "Unobstructed vistas of the Pacific coastline"),
            ("High-Speed Fiber Wi-Fi", "wifi", Amenity.Category.TECH, "Complimentary gigabit wireless connection"),
            ("Plush King Bed & Egyptian Linens", "bed", Amenity.Category.COMFORT, "Custom 1000-thread count luxury mattress"),
            ("Ensuite Jacuzzi Soaking Tub", "bath", Amenity.Category.BATHROOM, "Marble deep tub with hydrotherapy jets"),
            ("Artisan Espresso Bar", "coffee", Amenity.Category.DINING, "Illy espresso machine with organic coffee pods"),
            ("Private Oceanfront Balcony", "sun", Amenity.Category.VIEW, "Furnished outdoor terrace for sunset dining"),
            ("Smart 65-inch 4K OLED TV", "tv", Amenity.Category.TECH, "Apple AirPlay & Netflix streaming integration"),
            ("Whisper-Quiet Climate Control AC", "wind", Amenity.Category.COMFORT, "Independent dual-zone temperature automation"),
            ("In-Room Gourmet Mini Bar", "box", Amenity.Category.DINING, "Artisan spirits, champagnes, and organic bites"),
            ("Executive Workstation", "briefcase", Amenity.Category.COMFORT, "Ergonomic Herman Miller chair and USB-C dock"),
        ]

        amenity_objs = {}
        for name, icon, cat, desc in amenities_data:
            a = Amenity.objects.create(name=name, icon=icon, category=cat, description=desc)
            amenity_objs[name] = a

        # 3. Room Types
        self.stdout.write(self.style.NOTICE("Creating Room Types & Pricing tiers..."))
        
        rt_penthouse = RoomType.objects.create(
            name="Presidential Oceanfront Penthouse",
            slug="presidential-oceanfront-penthouse",
            tagline="The pinnacle of luxury with panoramic coastline terraces and private jacuzzi.",
            description="Perched on the highest floor, the Presidential Penthouse offers expansive living and dining salons, custom Italian furniture, a master sanctuary with ensuite marble bath, and private terrace.",
            base_price=Decimal('650.00'),
            weekend_price=Decimal('780.00'),
            max_guests=4,
            bed_type="1 King Bed + 1 Queen Murphy",
            size_sqft=1250,
            image_url="https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=1000&q=80"
        )
        rt_penthouse.amenities.set(list(amenity_objs.values()))

        rt_executive = RoomType.objects.create(
            name="Executive Oceanview Suite",
            slug="executive-oceanview-suite",
            tagline="Sublime coastal elegance tailored for discerning travelers and prolonged stays.",
            description="Features separate living lounge, panoramic floor-to-ceiling windows, marble bathroom, and dedicated workspace with premium acoustic isolation.",
            base_price=Decimal('380.00'),
            weekend_price=Decimal('440.00'),
            max_guests=3,
            bed_type="1 King Bed",
            size_sqft=720,
            image_url="https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=1000&q=80"
        )
        rt_executive.amenities.set([
            amenity_objs["Panoramic Ocean View"],
            amenity_objs["High-Speed Fiber Wi-Fi"],
            amenity_objs["Plush King Bed & Egyptian Linens"],
            amenity_objs["Artisan Espresso Bar"],
            amenity_objs["Private Oceanfront Balcony"],
            amenity_objs["Smart 65-inch 4K OLED TV"],
            amenity_objs["Whisper-Quiet Climate Control AC"],
            amenity_objs["Executive Workstation"]
        ])

        rt_deluxe = RoomType.objects.create(
            name="Deluxe Double Queen Room",
            slug="deluxe-double-queen-room",
            tagline="Spacious dual-bed comfort ideal for families and corporate partners.",
            description="Boasts two plush queen beds, oversized rainfall shower, luxury bathrobes, ergonomic workstation, and artisanal tea and espresso bar.",
            base_price=Decimal('260.00'),
            weekend_price=Decimal('310.00'),
            max_guests=4,
            bed_type="2 Queen Beds",
            size_sqft=540,
            image_url="https://images.unsplash.com/photo-1566665797739-1674de7a421a?auto=format&fit=crop&w=1000&q=80"
        )
        rt_deluxe.amenities.set([
            amenity_objs["High-Speed Fiber Wi-Fi"],
            amenity_objs["Smart 65-inch 4K OLED TV"],
            amenity_objs["Whisper-Quiet Climate Control AC"],
            amenity_objs["Artisan Espresso Bar"],
            amenity_objs["In-Room Gourmet Mini Bar"]
        ])

        rt_classic = RoomType.objects.create(
            name="Classic King Comfort Studio",
            slug="classic-king-comfort-studio",
            tagline="Refined, whisper-quiet retreat with plush king bedding and modern amenities.",
            description="Intelligently appointed for restorative sleep and seamless connectivity, featuring boutique amenities and designer lighting.",
            base_price=Decimal('185.00'),
            weekend_price=Decimal('215.00'),
            max_guests=2,
            bed_type="1 King Bed",
            size_sqft=420,
            image_url="https://images.unsplash.com/photo-1618773928121-c32242e63f39?auto=format&fit=crop&w=1000&q=80"
        )
        rt_classic.amenities.set([
            amenity_objs["High-Speed Fiber Wi-Fi"],
            amenity_objs["Plush King Bed & Egyptian Linens"],
            amenity_objs["Smart 65-inch 4K OLED TV"],
            amenity_objs["Whisper-Quiet Climate Control AC"]
        ])

        # 4. Physical Rooms
        self.stdout.write(self.style.NOTICE("Creating Physical Rooms inventory..."))
        rooms_data = [
            # Floor 1
            ("101", rt_classic, 1, Room.Status.AVAILABLE, "Turn-down service ready"),
            ("102", rt_classic, 1, Room.Status.DIRTY, "Checked out today. Housekeeping sanitization scheduled"),
            ("103", rt_deluxe, 1, Room.Status.AVAILABLE, "Inspected and sealed"),
            ("104", rt_deluxe, 1, Room.Status.MAINTENANCE, "Routine HVAC filter replacement in progress"),
            
            # Floor 2
            ("201", rt_deluxe, 2, Room.Status.OCCUPIED, "VIP guest in residence"),
            ("202", rt_deluxe, 2, Room.Status.AVAILABLE, "Ready for guest check-in"),
            ("203", rt_executive, 2, Room.Status.AVAILABLE, "Ready for guest check-in"),
            ("204", rt_executive, 2, Room.Status.AVAILABLE, "Ready for guest check-in"),

            # Floor 3
            ("301", rt_executive, 3, Room.Status.AVAILABLE, "Pre-arrival inspection completed"),
            ("302", rt_executive, 3, Room.Status.AVAILABLE, "Ready for guest check-in"),
            ("303", rt_executive, 3, Room.Status.AVAILABLE, "Ready for guest check-in"),

            # Floor 4 (Penthouse)
            ("PH-01", rt_penthouse, 4, Room.Status.AVAILABLE, "Welcome champagne chilled"),
            ("PH-02", rt_penthouse, 4, Room.Status.AVAILABLE, "Penthouse sanctuary inspected"),
        ]

        rooms_dict = {}
        for r_num, r_type, fl, st, notes in rooms_data:
            r = Room.objects.create(
                room_number=r_num,
                room_type=r_type,
                floor=fl,
                status=st,
                housekeeping_notes=notes
            )
            rooms_dict[r_num] = r

        # 5. Realistic Seed Reservations & History
        today = timezone.localdate()
        self.stdout.write(self.style.NOTICE("Creating Realistic Booking Records & Audit Trail..."))

        # Reservation 1: Currently In-House (Checked In)
        # Room 201: Checked in yesterday, checking out tomorrow
        in_house_in = today - timedelta(days=1)
        in_house_out = today + timedelta(days=2)
        pricing1 = BookingService.calculate_pricing(rt_deluxe, in_house_in, in_house_out, guests_count=2, has_breakfast=True)
        res1 = Reservation.objects.create(
            booking_reference="GV-2026-8812",
            guest=guest_user,
            guest_name=guest_user.get_full_name(),
            guest_email=guest_user.email,
            guest_phone=guest_user.phone_number,
            special_requests="High floor requested, allergic to feathers",
            room=rooms_dict["201"],
            room_type=rt_deluxe,
            check_in=in_house_in,
            check_out=in_house_out,
            guests_count=2,
            status=Reservation.Status.CHECKED_IN,
            nightly_rate=pricing1['average_nightly_rate'],
            num_nights=pricing1['num_nights'],
            room_subtotal=pricing1['room_subtotal'],
            tax_amount=pricing1['tax_amount'],
            service_fee=pricing1['service_fee'],
            addons_amount=pricing1['addons_total'],
            total_amount=pricing1['total_amount'],
            payment_status=Reservation.PaymentStatus.PAID,
            payment_method='SANDBOX_CARD',
            transaction_id='TXN-SB-881290',
            paid_at=timezone.now() - timedelta(days=2),
            checked_in_at=timezone.now() - timedelta(days=1)
        )
        BookingAuditLog.objects.create(
            reservation=res1,
            room=rooms_dict["201"],
            user=staff_user,
            action=BookingAuditLog.Action.CHECKED_IN,
            title="Guest Checked In: David Miller",
            details="Front desk verified ID and issued digital key for Room 201."
        )

        # Reservation 2: Today's Arrival (Confirmed, awaiting check-in)
        # Room 301: Check in today, check out in 3 days
        arrival_in = today
        arrival_out = today + timedelta(days=3)
        pricing2 = BookingService.calculate_pricing(rt_executive, arrival_in, arrival_out, guests_count=1, has_shuttle=True)
        res2 = Reservation.objects.create(
            booking_reference="GV-2026-9421",
            guest=guest2_user,
            guest_name=guest2_user.get_full_name(),
            guest_email=guest2_user.email,
            guest_phone=guest2_user.phone_number,
            special_requests="Late check-in anticipated around 6:00 PM",
            room=rooms_dict["301"],
            room_type=rt_executive,
            check_in=arrival_in,
            check_out=arrival_out,
            guests_count=1,
            status=Reservation.Status.CONFIRMED,
            nightly_rate=pricing2['average_nightly_rate'],
            num_nights=pricing2['num_nights'],
            room_subtotal=pricing2['room_subtotal'],
            tax_amount=pricing2['tax_amount'],
            service_fee=pricing2['service_fee'],
            addons_amount=pricing2['addons_total'],
            total_amount=pricing2['total_amount'],
            payment_status=Reservation.PaymentStatus.PAID,
            payment_method='SANDBOX_CARD',
            transaction_id='TXN-SB-942103',
            paid_at=timezone.now() - timedelta(days=1)
        )
        BookingAuditLog.objects.create(
            reservation=res2,
            room=rooms_dict["301"],
            user=guest2_user,
            action=BookingAuditLog.Action.BOOKING_CONFIRMED,
            title="Reservation Confirmed: Sarah Jenkins",
            details=f"Booked Room 301 for 3 nights. Airport shuttle requested."
        )

        # Reservation 3: Upcoming Future Reservation next week
        # Room 101: 5 days from today
        future_in = today + timedelta(days=5)
        future_out = today + timedelta(days=8)
        pricing3 = BookingService.calculate_pricing(rt_classic, future_in, future_out, guests_count=2)
        res3 = Reservation.objects.create(
            booking_reference="GV-2026-1049",
            guest=guest_user,
            guest_name=guest_user.get_full_name(),
            guest_email=guest_user.email,
            guest_phone=guest_user.phone_number,
            special_requests="Extra towels and quiet room",
            room=rooms_dict["101"],
            room_type=rt_classic,
            check_in=future_in,
            check_out=future_out,
            guests_count=2,
            status=Reservation.Status.CONFIRMED,
            nightly_rate=pricing3['average_nightly_rate'],
            num_nights=pricing3['num_nights'],
            room_subtotal=pricing3['room_subtotal'],
            tax_amount=pricing3['tax_amount'],
            service_fee=pricing3['service_fee'],
            addons_amount=pricing3['addons_total'],
            total_amount=pricing3['total_amount'],
            payment_status=Reservation.PaymentStatus.PAID,
            payment_method='SANDBOX_CARD',
            transaction_id='TXN-SB-104958',
            paid_at=timezone.now() - timedelta(hours=6)
        )

        # Reservation 4: Past Completed Stay (Checked out 2 days ago)
        # Room 102
        past_in = today - timedelta(days=4)
        past_out = today - timedelta(days=1)
        pricing4 = BookingService.calculate_pricing(rt_classic, past_in, past_out, guests_count=1)
        res4 = Reservation.objects.create(
            booking_reference="GV-2026-7731",
            guest=guest2_user,
            guest_name=guest2_user.get_full_name(),
            guest_email=guest2_user.email,
            guest_phone=guest2_user.phone_number,
            room=rooms_dict["102"],
            room_type=rt_classic,
            check_in=past_in,
            check_out=past_out,
            guests_count=1,
            status=Reservation.Status.CHECKED_OUT,
            nightly_rate=pricing4['average_nightly_rate'],
            num_nights=pricing4['num_nights'],
            room_subtotal=pricing4['room_subtotal'],
            tax_amount=pricing4['tax_amount'],
            service_fee=pricing4['service_fee'],
            addons_amount=pricing4['addons_total'],
            total_amount=pricing4['total_amount'],
            payment_status=Reservation.PaymentStatus.PAID,
            payment_method='SANDBOX_CARD',
            transaction_id='TXN-SB-773199',
            paid_at=timezone.now() - timedelta(days=5),
            checked_in_at=timezone.now() - timedelta(days=4),
            checked_out_at=timezone.now() - timedelta(days=1)
        )
        BookingAuditLog.objects.create(
            reservation=res4,
            room=rooms_dict["102"],
            user=staff_user,
            action=BookingAuditLog.Action.CHECKED_OUT,
            title="Guest Checked Out: Sarah Jenkins",
            details="Completed 3-night stay. Room 102 transitioned to DIRTY/CLEANING."
        )

        # Reservation 5: Cancelled Stay with Refund
        res5 = Reservation.objects.create(
            booking_reference="GV-2026-4402",
            guest=guest_user,
            guest_name=guest_user.get_full_name(),
            guest_email=guest_user.email,
            guest_phone=guest_user.phone_number,
            room=rooms_dict["202"],
            room_type=rt_deluxe,
            check_in=today + timedelta(days=12),
            check_out=today + timedelta(days=15),
            guests_count=2,
            status=Reservation.Status.CANCELLED,
            nightly_rate=Decimal('260.00'),
            num_nights=3,
            room_subtotal=Decimal('780.00'),
            tax_amount=Decimal('93.60'),
            service_fee=Decimal('39.00'),
            addons_amount=Decimal('0.00'),
            total_amount=Decimal('912.60'),
            payment_status=Reservation.PaymentStatus.REFUNDED,
            payment_method='SANDBOX_CARD',
            transaction_id='TXN-SB-440211',
            paid_at=timezone.now() - timedelta(days=3),
            cancelled_at=timezone.now() - timedelta(days=1),
            cancellation_reason="Guest flight cancelled due to storm"
        )
        BookingAuditLog.objects.create(
            reservation=res5,
            room=rooms_dict["202"],
            user=guest_user,
            action=BookingAuditLog.Action.CANCELLED,
            title="Reservation Cancelled: David Miller",
            details="Cancellation processed with full refund. Room 202 restored to inventory."
        )

        # Active Temporary Hold: Penthouse PH-01 (15-min hold)
        hold_in = today + timedelta(days=10)
        hold_out = today + timedelta(days=14)
        pricing_hold = BookingService.calculate_pricing(rt_penthouse, hold_in, hold_out, guests_count=2)
        hold = BookingHold.objects.create(
            room=rooms_dict["PH-01"],
            room_type=rt_penthouse,
            guest=guest_user,
            check_in=hold_in,
            check_out=hold_out,
            guests_count=2,
            estimated_total=pricing_hold['total_amount'],
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        BookingAuditLog.objects.create(
            room=rooms_dict["PH-01"],
            user=guest_user,
            action=BookingAuditLog.Action.HOLD_CREATED,
            title="Temporary Hold Active: Penthouse PH-01",
            details=f"Hold {hold.hold_id} locked for 15 minutes."
        )

        self.stdout.write(self.style.SUCCESS(
            "\n" + "-"*60 + "\n"
            "GRANDVIEW HOTEL SEED DATA APPLIED SUCCESSFULLY!\n"
            "-"*60 + "\n"
            "Demo Credentials (1-Click login buttons on /accounts/login/):\n"
            "  * Administrator: admin@grandview.com / adminpassword123\n"
            "  * Front Desk:    staff@grandview.com / staffpassword123\n"
            "  * Guest 1:       guest@example.com   / guestpassword123\n"
            "  * Guest 2:       sarah@example.com   / guestpassword123\n"
            "-"*60
        ))
