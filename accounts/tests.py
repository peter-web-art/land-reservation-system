from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from datetime import date

from .models import User, SystemSettings
from lands.models import Land, Reservation, PaymentRecord


# Tests removed after KYC removal.


class AdminPlatformFeeTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='adminuser',
            password='pass12345',
            email='admin@example.com',
            role=User.ROLE_ADMIN,
            is_staff=True,
        )
        SystemSettings.objects.create(platform_fee_percentage='5.00')

    def test_admin_can_update_platform_fee_percentage(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('accounts:admin_system_action'),
            {
                'action': 'save_platform_fee',
                'platform_fee_percentage': '12.50',
            },
        )

        settings_obj = SystemSettings.objects.first()
        self.assertRedirects(response, reverse('accounts:admin_portal'))
        self.assertEqual(str(settings_obj.platform_fee_percentage), '12.50')

    def test_admin_portal_shows_earnings_by_owner_and_property(self):
        owner = User.objects.create_user(
            username='plotowner',
            password='pass12345',
            email='owner@example.com',
            role=User.ROLE_OWNER,
            is_owner=True,
        )
        customer = User.objects.create_user(
            username='buyer',
            password='pass12345',
            email='buyer@example.com',
        )
        land = Land.objects.create(
            owner=owner,
            title='Hill Plot',
            description='Nice plot',
            location='Moshi',
            price='300000.00',
            price_unit='total',
            usage='sale',
            land_use='residential',
        )
        reservation = Reservation.objects.create(
            land=land,
            customer=customer,
            customer_name='Buyer',
            customer_email='buyer@example.com',
            status='approved',
        )
        PaymentRecord.objects.create(
            reservation=reservation,
            amount='100000.00',
            payment_method='bank',
            payment_reference='OWN123',
            payment_date=date.today(),
            status='confirmed',
            platform_fee_rate='5.00',
            platform_fee_amount='5000.00',
        )

        self.client.force_login(self.admin)
        response = self.client.get(reverse('accounts:admin_portal'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Earnings by Owner')
        self.assertContains(response, 'plotowner')
        self.assertContains(response, 'Hill Plot')
