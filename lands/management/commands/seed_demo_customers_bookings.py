from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import OperatorPaymentConfig, PersonalDetails, User
from lands.models import PaymentRecord, Reservation, Land


DEMO_CUSTOMERS = [
    ('Asha', 'Juma'),
    ('Neema', 'Msuya'),
    ('Baraka', 'Kweka'),
    ('Faith', 'Magesa'),
    ('Eliza', 'Mollel'),
    ('Daniel', 'Sanga'),
    ('Zawadi', 'Mrema'),
    ('Moses', 'Kimaro'),
    ('Rehema', 'Mchome'),
    ('Julius', 'Nyerere'),
    ('Halima', 'Mwakalonge'),
    ('Peter', 'Mushi'),
    ('Sofia', 'Mtei'),
    ('John', 'Morrison'),
    ('Hawa', 'Mnyema'),
    ('Samuel', 'Kileo'),
    ('Lilian', 'Mbise'),
    ('Abdallah', 'Suleiman'),
    ('Mariam', 'Nassoro'),
    ('Emmanuel', 'Mushi'),
]


class Command(BaseCommand):
    help = 'Create demo customer accounts, demo lands, and reservations for richer sample data.'

    def add_arguments(self, parser):
        parser.add_argument('--customers', type=int, default=20, help='Number of customers to create.')
        parser.add_argument('--bookings', type=int, default=20, help='Number of bookings to create.')
        parser.add_argument('--lands', type=int, default=6, help='Number of demo lands to create.')
        parser.add_argument('--prefix', type=str, default='demo', help='Username prefix for created customers.')

    def handle(self, *args, **options):
        customer_count = max(1, min(int(options['customers']), 20))
        booking_count = max(1, min(int(options['bookings']), 30))
        land_count = max(0, min(int(options['lands']), 10))
        prefix = options['prefix'].strip() or 'demo'

        payment_configs = self._ensure_payment_configs()
        demo_owner = self._ensure_demo_owner()
        self._ensure_demo_lands(demo_owner, land_count)

        active_lands = list(
            Land.objects.filter(is_active=True, is_draft=False).select_related('owner').order_by('id')
        )
        if not active_lands:
            self.stdout.write(self.style.ERROR('No active lands found. Seed land listings first.'))
            return

        customer_rows = DEMO_CUSTOMERS[:customer_count]
        booking_statuses = [
            'pending', 'awaiting_payment', 'approved', 'awaiting_payment', 'pending',
            'approved', 'awaiting_payment', 'pending', 'approved', 'awaiting_payment',
            'pending', 'awaiting_payment', 'approved', 'pending', 'approved',
            'awaiting_payment', 'pending', 'approved', 'awaiting_payment', 'pending',
            'approved', 'awaiting_payment', 'pending', 'approved', 'awaiting_payment',
            'pending', 'approved', 'awaiting_payment', 'pending', 'approved',
        ]
        payment_methods = [
            'mpesa', 'airtel', 'bank', 'cash', 'mpesa',
            'bank', 'airtel', 'cash', 'mpesa', 'bank',
            'airtel', 'mpesa', 'bank', 'cash', 'mpesa',
            'bank', 'airtel', 'cash', 'mpesa', 'bank',
            'airtel', 'mpesa', 'bank', 'cash', 'mpesa',
            'bank', 'airtel', 'cash', 'mpesa', 'bank',
        ]

        created_customers = 0
        created_bookings = 0
        created_payments = 0
        created_lands = 0

        with transaction.atomic():
            for idx in range(land_count):
                title = f'Demo Land {idx + 1:02d}'
                land, land_created = Land.objects.get_or_create(
                    owner=demo_owner,
                    title=title,
                    defaults={
                        'description': f'Demo land listing number {idx + 1}.',
                        'region': 'arusha',
                        'district': 'Arusha City',
                        'ward': f'Demo Ward {idx + 1}',
                        'street': f'Demo Street {idx + 1}',
                        'usage': 'rent' if idx % 2 == 0 else 'sale',
                        'size': Decimal('5.00') + Decimal(idx),
                        'size_unit': 'acres',
                        'land_use': 'agricultural' if idx % 2 == 0 else 'residential',
                        'topography': 'flat',
                        'soil_fertility': 'moderate',
                        'price': Decimal('250000') + (Decimal(idx) * Decimal('50000')),
                        'price_unit': 'month' if idx % 2 == 0 else 'total',
                        'contact_phone': f'0714000{idx + 1:03d}',
                        'contact_email': f'demoland{idx + 1:02d}@example.com',
                        'owner_will_refund': True,
                        'is_active': True,
                        'is_draft': False,
                    },
                )
                if land_created:
                    created_lands += 1

            for idx in range(customer_count):
                first_name, surname = customer_rows[idx % len(customer_rows)]
                username = f'{prefix}_customer_{idx + 1:02d}'
                email = f'{username}@example.com'
                phone = f'07{(idx + 1):08d}'[:10]

                user, user_created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'email': email,
                        'role': User.ROLE_CUSTOMER,
                    },
                )
                if user_created:
                    user.set_password('DemoPass123!')
                user.email = email
                user.role = User.ROLE_CUSTOMER
                user.is_owner = False
                user.is_staff = False
                user.save()
                if user_created:
                    created_customers += 1

                PersonalDetails.objects.update_or_create(
                    user=user,
                    defaults={
                        'fname': first_name,
                        'mname': '',
                        'surname': surname,
                        'address': f'{surname} Street, Demo Ward',
                        'phone': phone,
                        'email': email,
                        'bio': f'Demo customer profile for {first_name} {surname}.',
                    },
                )

                land = active_lands[idx % len(active_lands)]
                status = booking_statuses[idx]
                payment_method = payment_methods[idx]
                payment_reference = ''
                selected_payment = None

                start_date = None
                end_date = None
                if land.usage == 'rent':
                    start_date = date.today() + timedelta(days=idx * 3 + 1)
                    end_date = start_date + timedelta(days=7)

                if status in ['awaiting_payment', 'approved']:
                    selected_payment = payment_configs.get(payment_method)
                    if idx % 2 == 1:
                        payment_reference = f'DEMO-{idx + 1:03d}-{land.land_id}'

                agreed_price = land.price or Decimal('0')
                reservation, booking_created = Reservation.objects.update_or_create(
                    land=land,
                    customer=user,
                    customer_name=f'{first_name} {surname}',
                    customer_email=email,
                    start_date=start_date,
                    end_date=end_date,
                    defaults={
                        'customer_phone': phone,
                        'status': status,
                        'payment_status': 'unpaid',
                        'payment_method': payment_method if status in ['awaiting_payment', 'approved'] else None,
                        'payment_reference': payment_reference or None,
                        'payment_confirmed': False,
                        'agreed_price': agreed_price,
                        'notes': f'Demo booking {idx + 1} created for dashboard data.',
                        'selected_operator_payment': selected_payment,
                    },
                )
                if booking_created:
                    created_bookings += 1

                if status in ['awaiting_payment', 'approved'] and payment_reference:
                    payment, payment_created = PaymentRecord.objects.get_or_create(
                        reservation=reservation,
                        payment_reference=payment_reference,
                        defaults={
                            'amount': agreed_price / Decimal('2') if agreed_price else Decimal('100000'),
                            'payment_method': payment_method,
                            'payment_date': date.today(),
                            'notes': 'Demo payment proof pending review.',
                            'status': 'submitted',
                        },
                    )
                    if payment_created:
                        created_payments += 1

        self.stdout.write(self.style.SUCCESS(
            f'Created/updated {created_lands} demo lands, {created_customers} customer accounts, {created_bookings} bookings, and {created_payments} submitted payments.'
        ))

    def _ensure_payment_configs(self):
        config_data = {
            'mpesa': {
                'account_identifier': '0712000001',
                'account_holder_name': 'Land Reserve Demo',
                'instructions': 'Pay via M-Pesa and keep the reference number.',
                'priority': 1,
            },
            'airtel': {
                'account_identifier': '0783000002',
                'account_holder_name': 'Land Reserve Demo',
                'instructions': 'Pay via Airtel Money and keep the reference number.',
                'priority': 2,
            },
            'bank_transfer': {
                'account_identifier': '001122334455',
                'account_holder_name': 'Land Reserve Demo',
                'bank_name': 'Demo Bank',
                'bank_branch': 'Main Branch',
                'instructions': 'Use bank transfer and keep the slip/reference.',
                'priority': 3,
            },
        }

        configs = {}
        for method, defaults in config_data.items():
            config, _ = OperatorPaymentConfig.objects.get_or_create(
                payment_method=method,
                defaults=defaults,
            )
            configs[method] = config
        return configs

    def _ensure_demo_owner(self):
        user, created = User.objects.get_or_create(
            username='demo_owner',
            defaults={
                'email': 'demo_owner@example.com',
                'role': User.ROLE_OWNER,
                'is_owner': True,
                'is_verified': True,
            },
        )
        if created:
            user.set_password('DemoPass123!')
        user.email = 'demo_owner@example.com'
        user.role = User.ROLE_OWNER
        user.is_owner = True
        user.is_verified = True
        user.save()
        PersonalDetails.objects.update_or_create(
            user=user,
            defaults={
                'fname': 'Demo',
                'mname': '',
                'surname': 'Owner',
                'address': 'Demo Business District',
                'phone': '0715000000',
                'email': 'demo_owner@example.com',
                'bio': 'Demo owner account used for sample land listings.',
            },
        )
        return user

    def _ensure_demo_lands(self, owner, land_count):
        if land_count <= 0:
            return

        demo_lands = [
            ('Demo Farm Alpha', 'arusha', 'Arusha City', 'Sakina', 'Alpha Street', 'rent', Decimal('6.00'), 'acres', 'agricultural', Decimal('300000'), 'month'),
            ('Demo Plot Beta', 'mwanza', 'Ilemela', 'Buzuruga', 'Beta Road', 'sale', Decimal('3.50'), 'acres', 'residential', Decimal('850000'), 'total'),
            ('Demo Field Gamma', 'dodoma', 'Dodoma City', 'Nzuguni', 'Gamma Avenue', 'rent', Decimal('8.00'), 'acres', 'agricultural', Decimal('420000'), 'month'),
            ('Demo Land Delta', 'mbeya', 'Mbeya City', 'Uyole', 'Delta Road', 'sale', Decimal('4.00'), 'acres', 'commercial', Decimal('1200000'), 'total'),
            ('Demo Farm Epsilon', 'kilimanjaro', 'Moshi Rural', 'Makoa', 'Epsilon Street', 'rent', Decimal('10.00'), 'acres', 'mixed', Decimal('500000'), 'month'),
            ('Demo Plot Zeta', 'tanga', 'Tanga City', 'Mchukwi', 'Zeta Lane', 'sale', Decimal('2.75'), 'acres', 'residential', Decimal('640000'), 'total'),
            ('Demo Field Eta', 'mwanza', 'Nyamagana', 'Kirumba', 'Eta Road', 'rent', Decimal('5.50'), 'acres', 'agricultural', Decimal('360000'), 'month'),
            ('Demo Land Theta', 'arusha', 'Arusha City', 'Njiro', 'Theta Avenue', 'sale', Decimal('3.00'), 'acres', 'commercial', Decimal('950000'), 'total'),
            ('Demo Farm Iota', 'dodoma', 'Bahi', 'Iota Ward', 'Iota Street', 'rent', Decimal('7.25'), 'acres', 'agricultural', Decimal('280000'), 'month'),
            ('Demo Plot Kappa', 'mbeya', 'Mbeya City', 'Kata', 'Kappa Road', 'sale', Decimal('1.80'), 'acres', 'residential', Decimal('700000'), 'total'),
        ]

        for idx, (title, region, district, ward, street, usage, size, size_unit, land_use, price, price_unit) in enumerate(demo_lands[:land_count]):
            Land.objects.get_or_create(
                owner=owner,
                title=title,
                defaults={
                    'description': f'Demo listing: {title}.',
                    'region': region,
                    'district': district,
                    'ward': ward,
                    'street': street,
                    'usage': usage,
                    'size': size,
                    'size_unit': size_unit,
                    'land_use': land_use,
                    'topography': 'flat',
                    'soil_fertility': 'moderate',
                    'price': price,
                    'price_unit': price_unit,
                    'contact_phone': f'0716000{idx + 1:03d}',
                    'contact_email': f'{title.lower().replace(" ", "")}@example.com',
                    'owner_will_refund': True,
                    'is_active': True,
                    'is_draft': False,
                },
            )
