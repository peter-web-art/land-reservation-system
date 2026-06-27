from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import PaymentDetails, PersonalDetails, User
from lands.models import Land, LandReport, Message, Notification, PaymentRecord, Reservation


class Command(BaseCommand):
    help = 'Seed demo owner payout and escrow data for presentation screens.'

    def add_arguments(self, parser):
        parser.add_argument('--records', type=int, default=10, help='Number of confirmed escrow records to seed.')
        parser.add_argument('--owner-prefix', type=str, default='demo_owner', help='Primary owner username prefix.')
        parser.add_argument('--customer-prefix', type=str, default='demo_escrow_customer', help='Customer username prefix.')

    def handle(self, *args, **options):
        record_count = max(4, min(int(options['records']), 20))
        owner_prefix = (options['owner_prefix'] or 'demo_owner').strip()
        customer_prefix = (options['customer_prefix'] or 'demo_escrow_customer').strip()

        self._ensure_demo_admin()
        owners = self._ensure_demo_owners(owner_prefix)
        customers = self._ensure_demo_customers(customer_prefix, max(record_count, 10))
        demo_lands = self._ensure_demo_lands(owners)

        seeded = self._seed_confirmed_payments(demo_lands, customers, record_count)
        self._seed_refund_requests(demo_lands, customers, owners)
        self._seed_notifications_and_messages(demo_lands, customers, owners)
        self._seed_reported_lands(demo_lands, customers)

        self.stdout.write(self.style.SUCCESS(
            f'Seeded {seeded} confirmed escrow payments across {len(owners)} owners, '
            f'{len(demo_lands)} lands, and {len(customers)} customers.'
        ))

    def _ensure_demo_admin(self):
        admin, created = User.objects.get_or_create(
            username='demo_admin',
            defaults={
                'email': 'demo_admin@example.com',
                'role': User.ROLE_ADMIN,
                'is_staff': True,
                'is_superuser': False,
            },
        )
        if created:
            admin.set_password('DemoPass123!')
        admin.email = 'demo_admin@example.com'
        admin.role = User.ROLE_ADMIN
        admin.is_staff = True
        admin.is_superuser = False
        admin.save()
        PersonalDetails.objects.update_or_create(
            user=admin,
            defaults={
                'fname': 'Demo',
                'mname': '',
                'surname': 'Admin',
                'address': 'Demo Operations Center',
                'phone': '0719000000',
                'email': 'demo_admin@example.com',
                'bio': 'Demo admin account for presentation and escrow management.',
            },
        )

    def _ensure_demo_owners(self, prefix):
        owner_specs = [
            (f'{prefix}_alpha', 'Alpha Owner', '0717000001', 'mpesa', '0717000001'),
            (f'{prefix}_beta', 'Beta Owner', '0717000002', 'bank_transfer', '012300001122'),
            (f'{prefix}_gamma', 'Gamma Owner', '0717000003', 'airtel', '0788000003'),
        ]

        owners = []
        for username, display_name, phone, payment_method, account_identifier in owner_specs:
            first_name, last_name = display_name.split(' ', 1)
            owner, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@example.com',
                    'role': User.ROLE_OWNER,
                    'is_owner': True,
                    'is_verified': True,
                },
            )
            if created:
                owner.set_password('DemoPass123!')
            owner.email = f'{username}@example.com'
            owner.role = User.ROLE_OWNER
            owner.is_owner = True
            owner.is_verified = True
            owner.is_staff = False
            owner.save()

            PersonalDetails.objects.update_or_create(
                user=owner,
                defaults={
                    'fname': first_name,
                    'mname': '',
                    'surname': last_name,
                    'address': f'{display_name} Business District',
                    'phone': phone,
                    'email': owner.email,
                    'bio': f'Demo owner account for {display_name.lower()}.',
                },
            )

            PaymentDetails.objects.update_or_create(
                user=owner,
                defaults={
                    'payment_method': payment_method,
                    'account_identifier': account_identifier,
                    'account_holder_name': display_name,
                    'bank_name': 'Demo Bank' if payment_method == 'bank_transfer' else '',
                    'bank_branch': 'Main Branch' if payment_method == 'bank_transfer' else '',
                    'is_verified': True,
                    'verified_on': timezone.now(),
                    'is_default': True,
                },
            )
            owners.append(owner)

        return owners

    def _ensure_demo_customers(self, prefix, count):
        names = [
            ('Asha', 'Juma'), ('Neema', 'Msuya'), ('Baraka', 'Kweka'),
            ('Faith', 'Magesa'), ('Eliza', 'Mollel'), ('Daniel', 'Sanga'),
            ('Zawadi', 'Mrema'), ('Moses', 'Kimaro'), ('Rehema', 'Mchome'),
            ('Julius', 'Nyerere'), ('Halima', 'Mwakalonge'), ('Peter', 'Mushi'),
        ]

        customers = []
        for idx in range(count):
            first_name, surname = names[idx % len(names)]
            username = f'{prefix}_{idx + 1:02d}'
            email = f'{username}@example.com'
            customer, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'role': User.ROLE_CUSTOMER,
                },
            )
            if created:
                customer.set_password('DemoPass123!')
            customer.email = email
            customer.role = User.ROLE_CUSTOMER
            customer.is_owner = False
            customer.is_staff = False
            customer.save()

            PersonalDetails.objects.update_or_create(
                user=customer,
                defaults={
                    'fname': first_name,
                    'mname': '',
                    'surname': surname,
                    'address': f'{surname} Street, Demo Ward',
                    'phone': f'07{idx + 1:08d}'[:10],
                    'email': email,
                    'bio': f'Demo customer profile for {first_name} {surname}.',
                },
            )
            customers.append(customer)

        return customers

    def _ensure_demo_lands(self, owners):
        land_specs = [
            ('Presentation Farm Alpha', owners[0], 'arusha', 'Arusha City', 'Sakina', 'Alpha Street', 'rent', Decimal('6.00'), 'agricultural', Decimal('300000'), 'month'),
            ('Presentation Plot Beta', owners[0], 'mwanza', 'Ilemela', 'Buzuruga', 'Beta Road', 'sale', Decimal('3.50'), 'residential', Decimal('850000'), 'total'),
            ('Presentation Field Gamma', owners[1], 'dodoma', 'Dodoma City', 'Nzuguni', 'Gamma Avenue', 'rent', Decimal('8.00'), 'agricultural', Decimal('420000'), 'month'),
            ('Presentation Land Delta', owners[1], 'mbeya', 'Mbeya City', 'Uyole', 'Delta Road', 'sale', Decimal('4.00'), 'commercial', Decimal('1200000'), 'total'),
            ('Presentation Farm Epsilon', owners[2], 'kilimanjaro', 'Moshi Rural', 'Makoa', 'Epsilon Street', 'rent', Decimal('10.00'), 'mixed', Decimal('500000'), 'month'),
            ('Presentation Plot Zeta', owners[2], 'tanga', 'Tanga City', 'Mchukwi', 'Zeta Lane', 'sale', Decimal('2.75'), 'residential', Decimal('640000'), 'total'),
        ]

        lands = []
        for idx, (title, owner, region, district, ward, street, usage, size, land_use, price, price_unit) in enumerate(land_specs):
            land, _ = Land.objects.get_or_create(
                owner=owner,
                title=title,
                defaults={
                    'description': f'Demo listing for presentation: {title}.',
                    'region': region,
                    'district': district,
                    'ward': ward,
                    'street': street,
                    'usage': usage,
                    'size': size,
                    'size_unit': 'acres',
                    'land_use': land_use,
                    'topography': 'flat',
                    'soil_fertility': 'moderate',
                    'price': price,
                    'price_unit': price_unit,
                    'contact_phone': f'0718000{idx + 1:03d}',
                    'contact_email': f'{title.lower().replace(" ", "")}@example.com',
                    'owner_will_refund': True,
                    'is_active': True,
                    'is_draft': False,
                },
            )
            lands.append(land)

        return lands

    def _seed_confirmed_payments(self, lands, customers, record_count):
        now = timezone.now()
        created_count = 0

        with transaction.atomic():
            for idx in range(record_count):
                land = lands[idx % len(lands)]
                customer = customers[idx % len(customers)]
                approved_amount = Decimal('250000') + (Decimal(idx) * Decimal('25000'))
                confirmed_on = now - timedelta(hours=2 + idx * 3)
                if idx >= 5:
                    confirmed_on = now - timedelta(days=2 + (idx - 5))

                reservation, _ = Reservation.objects.get_or_create(
                    land=land,
                    customer=customer,
                    customer_name=f'{customer.first_name or customer.username} {customer.last_name or ""}'.strip(),
                    customer_email=customer.email,
                    defaults={
                        'customer_phone': getattr(customer, 'phone', '') or f'07{idx + 3:08d}'[:10],
                        'status': 'approved',
                        'payment_status': 'paid',
                        'payment_confirmed': True,
                        'payment_method': 'mpesa',
                        'payment_reference': f'ESCROW-{idx + 1:03d}',
                        'payment_date': date.today() - timedelta(days=min(idx, 6)),
                        'agreed_price': approved_amount,
                        'amount_paid': approved_amount,
                        'notes': f'Presentation escrow booking #{idx + 1}.',
                        'selected_operator_payment': None,
                    },
                )

                reservation.status = 'approved'
                reservation.payment_status = 'paid'
                reservation.payment_confirmed = True
                reservation.payment_method = 'mpesa'
                reservation.payment_reference = f'ESCROW-{idx + 1:03d}'
                reservation.payment_date = date.today() - timedelta(days=min(idx, 6))
                reservation.agreed_price = approved_amount
                reservation.amount_paid = approved_amount
                reservation.save()

                payment, payment_created = PaymentRecord.objects.update_or_create(
                    reservation=reservation,
                    payment_reference=f'ESCROW-{idx + 1:03d}',
                    defaults={
                        'amount': approved_amount,
                        'payment_method': 'mpesa',
                        'payment_date': date.today() - timedelta(days=min(idx, 6)),
                        'notes': 'Demo escrow payment for presentation.',
                        'status': 'confirmed',
                        'confirmed_on': confirmed_on,
                        'owner_received_on': None if idx < 5 else now - timedelta(days=1),
                    },
                )

                if payment_created:
                    created_count += 1

        return created_count

    def _seed_refund_requests(self, lands, customers, owners):
        refund_pairs = [
            (lands[0], customers[1], owners[0], 'The customer wants to change the project site after approval.'),
            (lands[2], customers[3], owners[1], 'The planned boundary has been revised and the booking is no longer needed.'),
        ]

        for idx, (land, customer, owner, reason) in enumerate(refund_pairs, start=1):
            reservation, _ = Reservation.objects.get_or_create(
                land=land,
                customer=customer,
                customer_name=f'{customer.first_name or customer.username} {customer.last_name or ""}'.strip(),
                customer_email=customer.email,
                defaults={
                    'customer_phone': getattr(customer, 'phone', '') or f'07{idx + 50:08d}'[:10],
                    'status': 'approved',
                    'payment_status': 'paid',
                    'payment_confirmed': True,
                    'payment_method': 'mpesa',
                    'payment_reference': f'REFUND-{idx:03d}',
                    'payment_date': date.today() - timedelta(days=idx),
                    'agreed_price': Decimal('350000') + (Decimal(idx) * Decimal('25000')),
                    'amount_paid': Decimal('350000') + (Decimal(idx) * Decimal('25000')),
                    'notes': f'Demo refund request #{idx}.',
                },
            )
            reservation.status = 'approved'
            reservation.payment_status = 'paid'
            reservation.payment_confirmed = True
            reservation.refund_requested = True
            reservation.refund_reason = reason
            reservation.refund_requested_on = timezone.now() - timedelta(days=idx)
            reservation.save()

            Notification.objects.get_or_create(
                user=owner,
                notification_type='payment',
                title='Refund Request Submitted',
                message=f'{customer.get_full_name() or customer.username} requested a refund for {land.title}.',
                link='/lands/payments/manage/?payment=refunds',
            )
            Notification.objects.get_or_create(
                user=customer,
                notification_type='payment',
                title='Refund Request Received',
                message=f'Your refund request for {land.title} is waiting for owner review.',
                link='/lands/my-bookings/',
            )

    def _seed_notifications_and_messages(self, lands, customers, owners):
        admin = User.objects.filter(username='demo_admin').first()
        if not admin:
            return

        notification_specs = [
            (owners[0], 'payment_received', 'Escrow released', f'Funds for {lands[0].title} are ready for release.', '/accounts/owner/payments/'),
            (owners[1], 'payment_received', 'Payment confirmed', f'Your payment on {lands[2].title} was confirmed.', '/accounts/owner/payments/'),
            (owners[2], 'system', 'Profile completed', 'Your payout details are verified and active.', '/accounts/owner/payments/'),
            (customers[0], 'booking_approved', 'Booking approved', f'{lands[0].title} is now approved. Continue payment to complete the booking.', '/lands/payments/'),
            (customers[1], 'payment', 'Payment under review', f'Your transaction for {lands[1].title} is being reviewed.', '/lands/payments/'),
            (admin, 'system', 'Escrow activity', 'Multiple confirmed payments are currently visible on the admin tracker.', '/accounts/admin-portal/escrow/'),
        ]

        for user, notification_type, title, message, link in notification_specs:
            Notification.objects.get_or_create(
                user=user,
                notification_type=notification_type,
                title=title,
                defaults={'message': message, 'link': link},
            )

        message_specs = [
            (admin, owners[0], lands[0], 'Payout Review', 'Please check the release window for the first batch of demo payments.'),
            (owners[0], admin, lands[0], 'Re: Payout Review', 'Confirmed. The release details are visible in the owner payment dashboard.'),
            (customers[0], owners[0], lands[0], 'Booking Question', 'I wanted to confirm the next step after approval.'),
            (owners[1], customers[3], lands[2], 'Payment Instructions', 'Use the payment options page and submit the reference number once paid.'),
            (admin, owners[2], lands[4], 'Refund Update', 'A refund request is visible in the dashboard for review.'),
        ]

        for sender, recipient, land, subject, body in message_specs:
            Message.objects.get_or_create(
                sender=sender,
                recipient=recipient,
                land=land,
                subject=subject,
                defaults={'body': body},
            )

    def _seed_reported_lands(self, lands, customers):
        report_specs = [
            (lands[0], customers[2], 'fake', 'Listing details appear inconsistent with the photos.'),
            (lands[3], customers[4], 'spam', 'Repeated promotional content was posted in the description.'),
            (lands[5], customers[5], 'duplicate', 'This appears to duplicate another listing nearby.'),
        ]

        for idx, (land, reporter, reason, description) in enumerate(report_specs, start=1):
            report, created = LandReport.objects.get_or_create(
                land=land,
                reported_by=reporter,
                defaults={
                    'reason': reason,
                    'description': description,
                    'status': 'submitted' if idx == 1 else 'reviewed',
                    'admin_notes': 'Demo report seeded for presentation.',
                    'is_spam': False,
                },
            )
            if created:
                if idx == 2:
                    report.status = 'reviewed'
                elif idx == 3:
                    report.status = 'resolved'
                report.save()
