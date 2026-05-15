from django.test import TestCase
from django.urls import reverse
from datetime import date

from accounts.models import User, SystemSettings
from .models import Land, Reservation, PaymentRecord


class LandAccessTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='owner',
            password='pass12345',
            email='owner@example.com',
            role=User.ROLE_OWNER,
            is_owner=True,
        )
        self.customer = User.objects.create_user(
            username='customer',
            password='pass12345',
            email='customer@example.com',
        )
        self.land = Land.objects.create(
            owner=self.owner,
            title='Ocean View Plot',
            description='A scenic parcel near the coast.',
            location='Dar es Salaam',
            price='1200.00',
            price_unit='month',
            usage='rent',
            land_use='residential',
        )

    def test_land_list_is_public(self):
        response = self.client.get(reverse('lands:land_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ocean View Plot')

    def test_land_detail_is_public(self):
        response = self.client.get(reverse('lands:land_detail', args=[self.land.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ocean View Plot')

    def test_send_message_ignores_external_referer_redirect(self):
        self.client.force_login(self.customer)

        response = self.client.post(
            reverse('lands:send_message'),
            {
                'recipient': str(self.owner.pk),
                'land': str(self.land.pk),
                'subject': 'Interested',
                'body': '',
            },
            HTTP_REFERER='https://evil.example/phish',
        )

        self.assertRedirects(response, reverse('lands:inbox'))


class PaymentTrackingTests(TestCase):
    def setUp(self):
        SystemSettings.objects.create(platform_fee_percentage='10.00')
        self.owner = User.objects.create_user(
            username='host',
            password='pass12345',
            email='host@example.com',
            role=User.ROLE_OWNER,
            is_owner=True,
        )
        self.customer = User.objects.create_user(
            username='buyer',
            password='pass12345',
            email='buyer@example.com',
        )
        self.land = Land.objects.create(
            owner=self.owner,
            title='Farm Block A',
            description='Fertile land.',
            location='Arusha',
            price='500000.00',
            price_unit='total',
            usage='sale',
            land_use='agricultural',
        )
        self.reservation = Reservation.objects.create(
            land=self.land,
            customer=self.customer,
            customer_name='Buyer One',
            customer_email='buyer@example.com',
            status='pending',
        )

    def test_customer_reference_submission_stays_unpaid_until_owner_confirms(self):
        self.client.force_login(self.customer)

        response = self.client.post(
            reverse('lands:submit_payment', args=[self.reservation.pk]),
            {
                'amount': '150000',
                'payment_method': 'bank',
                'payment_reference': 'ABC123XYZ',
                'payment_date': date.today().isoformat(),
                'notes': 'Paid via transfer',
            },
        )

        self.reservation.refresh_from_db()
        payment = PaymentRecord.objects.get(reservation=self.reservation)
        self.assertRedirects(response, reverse('lands:payments_and_bills'))
        self.assertEqual(self.reservation.payment_status, 'unpaid')
        self.assertFalse(self.reservation.payment_confirmed)
        self.assertEqual(self.reservation.payment_reference, 'ABC123XYZ')
        self.assertEqual(str(payment.amount), '150000.00')
        self.assertEqual(str(self.reservation.remaining_balance), '500000.00')

    def test_owner_confirmation_updates_paid_and_remaining_balance(self):
        payment = PaymentRecord.objects.create(
            reservation=self.reservation,
            amount='150000.00',
            payment_method='bank',
            payment_reference='ABC123XYZ',
            payment_date=date.today(),
            created_by=self.customer,
            updated_by=self.customer,
        )
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse('lands:confirm_payment_receipt', args=[self.reservation.pk]),
            {'action': 'confirm', 'payment_id': payment.pk},
        )

        self.reservation.refresh_from_db()
        payment.refresh_from_db()
        self.assertRedirects(response, reverse('lands:manage_payments'))
        self.assertFalse(self.reservation.payment_confirmed)
        self.assertEqual(self.reservation.payment_status, 'unpaid')
        self.assertEqual(self.reservation.status, 'approved')
        self.assertEqual(payment.status, 'confirmed')
        self.assertEqual(str(payment.platform_fee_rate), '10.00')
        self.assertEqual(str(payment.platform_fee_amount), '15000.00')
        self.assertEqual(str(self.reservation.confirmed_amount_total), '150000.00')
        self.assertEqual(str(self.reservation.remaining_balance), '350000.00')

    def test_approval_with_reference_does_not_auto_mark_payment_paid(self):
        self.reservation.payment_reference = 'ABC123XYZ'
        self.reservation.save()
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse('lands:update_reservation_status', args=[self.reservation.pk, 'approved']),
        )

        self.reservation.refresh_from_db()
        self.assertRedirects(response, reverse('lands:reservations_management'))
        self.assertEqual(self.reservation.status, 'approved')
        self.assertEqual(self.reservation.payment_status, 'unpaid')
        self.assertFalse(self.reservation.payment_confirmed)

    def test_second_installment_cannot_exceed_remaining_balance(self):
        PaymentRecord.objects.create(
            reservation=self.reservation,
            amount='400000.00',
            payment_method='bank',
            payment_reference='FIRST123',
            payment_date=date.today(),
            status='confirmed',
        )
        self.reservation.amount_paid = '400000.00'
        self.reservation.save()

        self.client.force_login(self.customer)
        response = self.client.post(
            reverse('lands:submit_payment', args=[self.reservation.pk]),
            {
                'amount': '150000',
                'payment_method': 'bank',
                'payment_reference': 'SECOND123',
                'payment_date': date.today().isoformat(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Amount cannot exceed remaining balance')

    def test_owner_net_total_excludes_platform_fee(self):
        PaymentRecord.objects.create(
            reservation=self.reservation,
            amount='200000.00',
            payment_method='bank',
            payment_reference='NET123',
            payment_date=date.today(),
            status='confirmed',
            platform_fee_rate='10.00',
            platform_fee_amount='20000.00',
        )

        self.assertEqual(str(self.reservation.confirmed_amount_total), '200000.00')
        self.assertEqual(str(self.reservation.platform_fee_total), '20000.00')
        self.assertEqual(str(self.reservation.owner_net_total), '180000.00')

    def test_payment_pages_load_for_customer_and_owner(self):
        self.client.force_login(self.customer)
        customer_response = self.client.get(reverse('lands:payments_and_bills'))
        self.assertEqual(customer_response.status_code, 200)
        self.assertContains(customer_response, 'Payments and Bills')

        self.client.force_login(self.owner)
        owner_response = self.client.get(reverse('lands:manage_payments'))
        self.assertEqual(owner_response.status_code, 200)
        self.assertContains(owner_response, 'Manage Payments')
