from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
from apps.accounts.models import User, CustomerProfile, WorkerProfile, WorkerAvailability
from apps.cooperatives.models import Cooperative, CooperativeMembership
from apps.services.models import ServiceCategory, ServiceItem, WorkerServiceOffer
from apps.bookings.models import Booking, BookingOTP
from apps.payments.models import PaymentTransaction, PlatformLedger
from apps.reviews.models import ServiceReview


class Command(BaseCommand):
    help = 'Seeds realistic industrial demo data for CoServe platform'

    def handle(self, *args, **options):
        self.stdout.write("Initializing database seeding for CoServe...")

        # 1. Superuser
        admin, created = User.objects.get_or_create(
            email='admin@coserve.org',
            defaults={
                'username': 'admin',
                'first_name': 'Platform',
                'last_name': 'Director',
                'role': User.Role.ADMIN,
                'is_staff': True,
                'is_superuser': True,
                'is_verified': True,
            }
        )
        if created:
            admin.set_password('adminpassword123')
            admin.save()
            self.stdout.write(self.style.SUCCESS("Created Superuser: admin@coserve.org / adminpassword123"))

        # 2. Cooperative Manager & Cooperative 1
        mgr1, _ = User.objects.get_or_create(
            email='manager.apex@coserve.org',
            defaults={
                'username': 'mgr_apex',
                'first_name': 'Kavita',
                'last_name': 'Menon',
                'role': User.Role.COOP_MANAGER,
                'phone_number': '+91 98450 11022',
                'is_verified': True,
            }
        )
        mgr1.set_password('manager123')
        mgr1.save()

        coop1, _ = Cooperative.objects.get_or_create(
            slug='apex-metro-craftsmen',
            defaults={
                'name': 'Apex Metro Craftsmen Cooperative',
                'registration_number': 'COOP-MH-2023-0091',
                'tagline': 'Certified Heavy Trade Guild: High-Voltage Electrical & Precision Piping',
                'description': 'A worker-owned cooperative providing enterprise-grade industrial trades, certified high-voltage electricians, precision HVAC engineers, and commercial pipefitters with verified safety compliance.',
                'manager': mgr1,
                'locality': 'Industrial Corridor, Phase 2',
                'city': 'Metropolis',
                'pincode': '400072',
                'latitude': 19.1136,
                'longitude': 72.8697,
                'service_radius_km': 25.0,
                'welfare_pool_percentage': Decimal('3.50'),
                'welfare_pool_balance': Decimal('14850.00'),
                'total_jobs_completed': 480,
            }
        )

        # Cooperative Manager & Cooperative 2
        mgr2, _ = User.objects.get_or_create(
            email='manager.alliance@coserve.org',
            defaults={
                'username': 'mgr_alliance',
                'first_name': 'Dinesh',
                'last_name': 'Rathore',
                'role': User.Role.COOP_MANAGER,
                'phone_number': '+91 98110 33455',
                'is_verified': True,
            }
        )
        mgr2.set_password('manager123')
        mgr2.save()

        coop2, _ = Cooperative.objects.get_or_create(
            slug='community-trades-alliance',
            defaults={
                'name': 'Community Trades & Structural Alliance',
                'registration_number': 'COOP-DL-2022-0442',
                'tagline': 'Federated Guild for Residential Repairs, Fabrication & Deep Sanitation',
                'description': 'Dedicated to neighborhood equity, transparent living wages, and reliable community home services. All members operate under mutual emergency support pools.',
                'manager': mgr2,
                'locality': 'Metro Civic Enclave',
                'city': 'Metropolis',
                'pincode': '400050',
                'latitude': 19.0596,
                'longitude': 72.8295,
                'service_radius_km': 20.0,
                'welfare_pool_percentage': Decimal('3.00'),
                'welfare_pool_balance': Decimal('9240.00'),
                'total_jobs_completed': 320,
            }
        )

        # 3. Service Categories (Industrial & Technical)
        categories_data = [
            {
                'name': 'Electrical & Power Systems',
                'code': 'ELEC-01',
                'slug': 'electrical-systems',
                'icon': 'bolt',
                'description': 'Heavy wiring, breaker panel overhaul, 3-phase balancing, surge arrestors, and commercial diagnostic inspections.'
            },
            {
                'name': 'Plumbing & Hydraulic Piping',
                'code': 'PLUMB-02',
                'slug': 'hydraulic-piping',
                'icon': 'wrench',
                'description': 'Commercial valve overhaul, mainline pressure testing, acoustic leak detection, drainage jetting, and sanitary installations.'
            },
            {
                'name': 'HVAC & Climate Engineering',
                'code': 'HVAC-03',
                'slug': 'hvac-climate',
                'icon': 'wind',
                'description': 'Industrial split system maintenance, chiller coil descaling, refrigerant charging, and duct airflow balancing.'
            },
            {
                'name': 'Carpentry, Metalwork & Fabrication',
                'code': 'FABR-04',
                'slug': 'fabrication-carpentry',
                'icon': 'hammer',
                'description': 'Structural wood assembly, aluminum profile installation, precision hinge alignment, and MIG/TIG metal repair.'
            },
            {
                'name': 'Heavy Sanitation & Industrial Scrubbing',
                'code': 'CLEAN-05',
                'slug': 'heavy-sanitation',
                'icon': 'sparkles',
                'description': 'Rotary floor decontamination, high-pressure degreasing, mold remediation, and complete post-renovation detailing.'
            },
        ]

        cats = {}
        for cdata in categories_data:
            cat, _ = ServiceCategory.objects.get_or_create(slug=cdata['slug'], defaults=cdata)
            cats[cdata['code']] = cat

        # 4. Service Items
        services_data = [
            {
                'cat_code': 'ELEC-01',
                'title': 'Distribution Board & Main Breaker Overhaul',
                'slug': 'main-breaker-overhaul',
                'base_price': Decimal('850.00'),
                'pricing_type': ServiceItem.PricingType.FIXED,
                'estimated_duration_minutes': 90,
                'tools_and_safety_specs': '1000V Insulated VDE toolkit, Digital Multimeter CAT-III, Arc Flash PPE Face Shield, lockout/tagout kit.',
                'description': 'Comprehensive diagnostic of panel busbars, tightening of terminal contacts, replacement of damaged MCB/RCCB units, and thermal testing.'
            },
            {
                'cat_code': 'ELEC-01',
                'title': 'Emergency Short Circuit Tracing & Remediation',
                'slug': 'short-circuit-tracing',
                'base_price': Decimal('650.00'),
                'pricing_type': ServiceItem.PricingType.FIXED,
                'estimated_duration_minutes': 60,
                'tools_and_safety_specs': 'Tone generator wire tracer, insulation resistance tester (Megger), VDE insulated pliers.',
                'description': 'Pinpoint isolation of hidden short circuits, wall conduit neutral fault detection, and wire restoration.'
            },
            {
                'cat_code': 'PLUMB-02',
                'title': 'Hydrostatic Mainline Pressure Test & Leak Repair',
                'slug': 'mainline-pressure-test',
                'base_price': Decimal('950.00'),
                'pricing_type': ServiceItem.PricingType.FIXED,
                'estimated_duration_minutes': 120,
                'tools_and_safety_specs': 'Manual hydrostatic test pump (50 Bar), pipe threading kit, acoustic geophone sensor, PTFE industrial sealant.',
                'description': 'Pressure stabilization of incoming water supply line, identification of concealed wall seepage, and union valve replacement.'
            },
            {
                'cat_code': 'PLUMB-02',
                'title': 'Motorized Overhead Tank Pump & Float Valve Setup',
                'slug': 'pump-float-valve-setup',
                'base_price': Decimal('750.00'),
                'pricing_type': ServiceItem.PricingType.FIXED,
                'estimated_duration_minutes': 75,
                'tools_and_safety_specs': 'Heavy pipe wrenches (18-inch), non-return check valves, Teflon thread paste, IP65 waterproof cable glands.',
                'description': 'Mounting and alignment of booster or submersible water pump, dual electromagnetic float sensor calibration, and inlet filtration.'
            },
            {
                'cat_code': 'HVAC-03',
                'title': 'Dual-Inverter AC Coil Jet Descaling & Chemical Flush',
                'slug': 'inverter-ac-jet-wash',
                'base_price': Decimal('1100.00'),
                'pricing_type': ServiceItem.PricingType.FIXED,
                'estimated_duration_minutes': 90,
                'tools_and_safety_specs': 'High-pressure foam jet cleaner (120 Bar), anti-corrosion coil wash chemical, drain catch funnel tarp, R32 pressure gauges.',
                'description': 'Deep indoor evaporator and outdoor condenser fin wash, clearing clogged condensate siphon lines, and refrigerant pressure audit.'
            },
            {
                'cat_code': 'FABR-04',
                'title': 'Reinforced Door Frame Alignment & Heavy Deadbolt Fabrication',
                'slug': 'deadbolt-fabrication',
                'base_price': Decimal('800.00'),
                'pricing_type': ServiceItem.PricingType.FIXED,
                'estimated_duration_minutes': 90,
                'tools_and_safety_specs': 'Laser level plumb line, orbital grinder, carbide drill bits, structural anchors.',
                'description': 'Precision mortising for security locks, leveling sagged timber/metal frames, and reinforcement of hinge strike plates.'
            },
            {
                'cat_code': 'CLEAN-05',
                'title': 'Heavy Alkaline Degreasing & Industrial Floor Scrubbing',
                'slug': 'industrial-floor-scrubbing',
                'base_price': Decimal('1400.00'),
                'pricing_type': ServiceItem.PricingType.FIXED,
                'estimated_duration_minutes': 150,
                'tools_and_safety_specs': 'Single-disc rotary floor scrubber (175 RPM), wet vacuum extractor, industrial degreaser, nitrile chemical gloves.',
                'description': 'Deep machine buffing of ceramic, terrazzo, or concrete tiles to eliminate heavy grease, cement film, and deep chemical stains.'
            },
        ]

        servs = {}
        for sdata in services_data:
            cat = cats[sdata.pop('cat_code')]
            svc, _ = ServiceItem.objects.get_or_create(
                slug=sdata['slug'],
                defaults={'category': cat, **sdata}
            )
            servs[sdata['slug']] = svc

        # 5. Workers (Trade Specialists)
        workers_data = [
            {
                'email': 'rajesh.kumar@coserve.org',
                'username': 'rajesh_electrician',
                'first_name': 'Rajesh',
                'last_name': 'Kumar',
                'phone': '+91 98200 44551',
                'gov_id_num': 'IND-AAD-8821-9031',
                'locality': 'Andheri East Industrial Zone',
                'pincode': '400069',
                'experience': 11,
                'rating_avg': Decimal('4.94'),
                'rating_count': 184,
                'jobs_completed': 312,
                'coop': coop1,
                'bio': 'Licensed Electrical Engineer & High-Voltage Systems Specialist. 11+ years handling industrial switchboards, commercial wiring, and safety-certified power distribution.',
                'services': ['main-breaker-overhaul', 'short-circuit-tracing'],
            },
            {
                'email': 'arun.patel@coserve.org',
                'username': 'arun_pipefitter',
                'first_name': 'Arun',
                'last_name': 'Patel',
                'phone': '+91 98330 66772',
                'gov_id_num': 'IND-AAD-7712-4411',
                'locality': 'Powai Tech Corridor',
                'pincode': '400076',
                'experience': 8,
                'rating_avg': Decimal('4.88'),
                'rating_count': 142,
                'jobs_completed': 228,
                'coop': coop1,
                'bio': 'Certified Master Plumber with specialization in hydrostatic pressure testing, concealed acoustic leak detection, and industrial booster pump setup.',
                'services': ['mainline-pressure-test', 'pump-float-valve-setup'],
            },
            {
                'email': 'vikram.singh@coserve.org',
                'username': 'vikram_hvac',
                'first_name': 'Vikram',
                'last_name': 'Singh',
                'phone': '+91 98190 22334',
                'gov_id_num': 'IND-AAD-6619-3321',
                'locality': 'Bandra West Enclave',
                'pincode': '400050',
                'experience': 9,
                'rating_avg': Decimal('4.91'),
                'rating_count': 116,
                'jobs_completed': 195,
                'coop': coop2,
                'bio': 'HVAC & Refrigeration technician. Expert in high-pressure coil flushing, multi-split inverter diagnostics, and commercial airflow duct calibration.',
                'services': ['inverter-ac-jet-wash'],
            },
            {
                'email': 'sunil.sharma@coserve.org',
                'username': 'sunil_fabricator',
                'first_name': 'Sunil',
                'last_name': 'Sharma',
                'phone': '+91 98670 99881',
                'gov_id_num': 'IND-AAD-5521-8899',
                'locality': 'Kalyan Industrial Belt',
                'pincode': '421301',
                'experience': 14,
                'rating_avg': Decimal('4.96'),
                'rating_count': 230,
                'jobs_completed': 410,
                'coop': coop2,
                'bio': 'Master Fabricator & Structural Carpenter. Specializing in high-security multi-point deadbolt installations, heavy hardwood frame repair, and structural metalwork.',
                'services': ['deadbolt-fabrication', 'industrial-floor-scrubbing'],
            },
        ]

        created_workers = []
        for wdata in workers_data:
            u, _ = User.objects.get_or_create(
                email=wdata['email'],
                defaults={
                    'username': wdata['username'],
                    'first_name': wdata['first_name'],
                    'last_name': wdata['last_name'],
                    'role': User.Role.WORKER,
                    'phone_number': wdata['phone'],
                    'is_verified': True,
                }
            )
            u.set_password('worker123')
            u.save()

            wp, _ = WorkerProfile.objects.get_or_create(
                user=u,
                defaults={
                    'gov_id_type': WorkerProfile.IdType.AADHAAR,
                    'gov_id_number': wdata['gov_id_num'],
                    'verification_status': WorkerProfile.VerificationStatus.VERIFIED,
                    'verified_at': timezone.now(),
                    'experience_years': wdata['experience'],
                    'bio': wdata['bio'],
                    'locality': wdata['locality'],
                    'city': 'Metropolis',
                    'pincode': wdata['pincode'],
                    'rating_avg': wdata['rating_avg'],
                    'rating_count': wdata['rating_count'],
                    'total_jobs_completed': wdata['jobs_completed'],
                    'is_available': True,
                    'accepts_cash_on_completion': True,
                    'cooperative': wdata['coop'],
                    'upi_id': f"{wdata['username']}@okaxis",
                }
            )
            created_workers.append(wp)

            # Cooperative Membership
            CooperativeMembership.objects.get_or_create(
                cooperative=wdata['coop'],
                worker=wp,
                defaults={
                    'status': CooperativeMembership.MembershipStatus.APPROVED,
                    'dividend_points': wdata['jobs_completed'] * 10,
                    'total_coop_earnings': Decimal(wdata['jobs_completed'] * 750),
                    'approved_at': timezone.now() - timedelta(days=120),
                }
            )

            # Assign service offers
            for s_slug in wdata['services']:
                if s_slug in servs:
                    WorkerServiceOffer.objects.get_or_create(
                        worker=wp,
                        service=servs[s_slug],
                        defaults={'is_active': True}
                    )

            # Default availability: Mon-Sat 08:00 - 18:00
            for day in range(6):
                WorkerAvailability.objects.get_or_create(
                    worker=wp,
                    day_of_week=day,
                    start_time='08:00:00',
                    defaults={'end_time': '18:00:00', 'is_active': True}
                )

        # 6. Customers (Households)
        customers_data = [
            {
                'email': 'rohit.sharma@example.com',
                'username': 'rohit_sharma',
                'first_name': 'Rohit',
                'last_name': 'Sharma',
                'phone': '+91 99100 22331',
                'address': 'Flat 702, Skyline Heights, Phase 1',
                'locality': 'Andheri West',
                'pincode': '400053',
            },
            {
                'email': 'priya.verma@example.com',
                'username': 'priya_verma',
                'first_name': 'Priya',
                'last_name': 'Verma',
                'phone': '+91 99200 44552',
                'address': 'Bungalow 14, Silver Oak Estate',
                'locality': 'Powai',
                'pincode': '400076',
            },
        ]

        created_customers = []
        for cdata in customers_data:
            u, _ = User.objects.get_or_create(
                email=cdata['email'],
                defaults={
                    'username': cdata['username'],
                    'first_name': cdata['first_name'],
                    'last_name': cdata['last_name'],
                    'role': User.Role.CUSTOMER,
                    'phone_number': cdata['phone'],
                    'is_verified': True,
                }
            )
            u.set_password('customer123')
            u.save()

            cp, _ = CustomerProfile.objects.get_or_create(
                user=u,
                defaults={
                    'address': cdata['address'],
                    'locality': cdata['locality'],
                    'city': 'Metropolis',
                    'pincode': cdata['pincode'],
                }
            )
            created_customers.append(cp)

        # 7. Sample Bookings demonstrating both modes and dual payment
        # Booking 1: Completed Booking with Review and Ledger (Direct + Online)
        b1, _ = Booking.objects.get_or_create(
            reference_code='CS-2026-B892',
            defaults={
                'customer': created_customers[0],
                'service': servs['main-breaker-overhaul'],
                'booking_mode': Booking.BookingMode.DIRECT,
                'worker': created_workers[0],
                'status': Booking.Status.COMPLETED,
                'scheduled_date': date.today() - timedelta(days=2),
                'time_slot': '09:00 - 11:00 AM',
                'service_address': 'Flat 702, Skyline Heights, Phase 1, Andheri West',
                'locality': 'Andheri West',
                'city': 'Metropolis',
                'pincode': '400053',
                'base_amount': Decimal('850.00'),
                'platform_fee': Decimal('42.50'),
                'coop_welfare_fee': Decimal('29.75'),
                'worker_earning': Decimal('777.75'),
                'total_amount': Decimal('850.00'),
                'payment_preference': Booking.PaymentPreference.ONLINE_APP,
                'payment_status': Booking.PaymentStatus.PAID_ONLINE,
            }
        )
        otp1, _ = BookingOTP.objects.get_or_create(
            booking=b1,
            defaults={
                'start_otp': '4821',
                'completion_otp': '9042',
                'is_start_verified': True,
                'is_completion_verified': True,
                'start_verified_at': timezone.now() - timedelta(days=2, hours=3),
                'completion_verified_at': timezone.now() - timedelta(days=2, hours=1),
            }
        )
        PaymentTransaction.objects.get_or_create(
            booking=b1,
            defaults={
                'channel': PaymentTransaction.Channel.RAZORPAY,
                'amount': Decimal('850.00'),
                'razorpay_order_id': 'order_rzp_mock_00192',
                'razorpay_payment_id': 'pay_mock_8819277',
                'status': PaymentTransaction.Status.SUCCESS,
            }
        )
        PlatformLedger.objects.get_or_create(
            booking=b1,
            defaults={
                'gross_amount': Decimal('850.00'),
                'platform_fee': Decimal('42.50'),
                'coop_welfare_fee': Decimal('29.75'),
                'worker_net_earning': Decimal('777.75'),
                'worker': created_workers[0],
                'cooperative': coop1,
                'is_settled': True,
                'settled_at': timezone.now() - timedelta(days=1),
            }
        )
        ServiceReview.objects.get_or_create(
            booking=b1,
            defaults={
                'customer': created_customers[0],
                'worker': created_workers[0],
                'rating': 5,
                'punctuality_rating': 5,
                'quality_rating': 5,
                'safety_compliance_rating': 5,
                'comment': 'Outstanding technician. Rajesh arrived on time in complete industrial PPE with CAT-III digital tester. Replaced the faulty Siemens RCCB and rebalanced panel phases in under an hour.',
                'worker_reply': 'Thank you Mr. Sharma! Glad we secured the distribution panel safely for your household.',
            }
        )

        # Booking 2: Active Booking in progress (Cooperative Mode + Pay on Completion)
        b2, _ = Booking.objects.get_or_create(
            reference_code='CS-2026-X771',
            defaults={
                'customer': created_customers[1],
                'service': servs['mainline-pressure-test'],
                'booking_mode': Booking.BookingMode.COOPERATIVE,
                'cooperative': coop1,
                'worker': created_workers[1],
                'status': Booking.Status.IN_PROGRESS,
                'scheduled_date': date.today(),
                'time_slot': '14:00 - 16:00 PM',
                'service_address': 'Bungalow 14, Silver Oak Estate, Powai',
                'locality': 'Powai',
                'city': 'Metropolis',
                'pincode': '400076',
                'base_amount': Decimal('950.00'),
                'platform_fee': Decimal('47.50'),
                'coop_welfare_fee': Decimal('33.25'),
                'worker_earning': Decimal('869.25'),
                'total_amount': Decimal('950.00'),
                'payment_preference': Booking.PaymentPreference.PAY_ON_COMPLETION,
                'payment_status': Booking.PaymentStatus.UNPAID,
            }
        )
        BookingOTP.objects.get_or_create(
            booking=b2,
            defaults={
                'start_otp': '7391',
                'completion_otp': '5184',
                'is_start_verified': True,
                'is_completion_verified': False,
                'start_verified_at': timezone.now() - timedelta(minutes=45),
            }
        )

        self.stdout.write(self.style.SUCCESS("[SUCCESS] Successfully seeded industrial services, trade workers, cooperatives, and demo workflows!"))
        self.stdout.write("=================================================================")
        self.stdout.write("DEMO ACCOUNTS READY TO TEST:")
        self.stdout.write("- Platform Admin:   admin@coserve.org           / adminpassword123")
        self.stdout.write("- Coop Manager:     manager.apex@coserve.org     / manager123")
        self.stdout.write("- Verified Worker:  rajesh.kumar@coserve.org     / worker123")
        self.stdout.write("- Customer:         rohit.sharma@example.com     / customer123")
        self.stdout.write("- Customer 2:       priya.verma@example.com      / customer123")
        self.stdout.write("=================================================================")
