import base64

from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from datetime import date

from accounts.models import OperatorPaymentConfig, User, SystemSettings
from .models import Land, Reservation, PaymentRecord


TEST_PNG_BYTES = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/7mQAAAAASUVORK5CYII='
)


def make_test_image(filename):
    return SimpleUploadedFile(filename, TEST_PNG_BYTES, content_type='image/png')


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

    def test_book_land_page_handles_missing_price(self):
        self.land.price = None
        self.land.save(update_fields=['price'])

        response = self.client.get(reverse('lands:book_land', args=[self.land.pk]))

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


class LandPublishWizardTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='wizard-owner',
            password='pass12345',
            email='wizard-owner@example.com',
            role=User.ROLE_OWNER,
            is_owner=True,
            is_verified=True,
        )

    def test_publish_land_accepts_selected_district(self):
        self.client.force_login(self.owner)

        payload = {
            'title': 'Meru Plot',
            'usage': 'rent',
            'land_use': 'residential',
            'price': '500000',
            'price_unit': 'month',
            'region': 'arusha',
            'district': 'Arusha City',
            'ward': 'Sekei',
            'street': 'Njiro Road',
            'size': '2.5',
            'size_unit': 'acres',
            'topography': 'flat',
            'soil_fertility': 'moderate',
            'contact_phone': '0712345678',
            'contact_email': 'wizard-owner@example.com',
            'owner_will_refund': 'True',
            'weekly_discount': '0',
            'monthly_discount': '0',
            'current_step': '6',
            'gallery_images': [
                make_test_image('photo-1.png'),
                make_test_image('photo-2.png'),
                make_test_image('photo-3.png'),
            ],
            'image_positions': ['north', 'south', 'aerial'],
        }

        response = self.client.post(reverse('lands:add_land'), payload)

        self.assertRedirects(response, reverse('lands:owner_dashboard'))
        land = Land.objects.get(title='Meru Plot')
        self.assertEqual(land.owner, self.owner)
        self.assertEqual(land.district, 'Arusha City')
        self.assertFalse(land.is_draft)

    def test_publish_land_rejects_duplicate_image_positions(self):
        self.client.force_login(self.owner)

        payload = {
            'title': 'Duplicate Positions Plot',
            'usage': 'rent',
            'land_use': 'residential',
            'price': '500000',
            'price_unit': 'month',
            'region': 'arusha',
            'district': 'Arusha City',
            'ward': 'Sekei',
            'street': 'Njiro Road',
            'size': '2.5',
            'size_unit': 'acres',
            'topography': 'flat',
            'soil_fertility': 'moderate',
            'contact_phone': '0712345678',
            'contact_email': 'wizard-owner@example.com',
            'owner_will_refund': 'True',
            'weekly_discount': '0',
            'monthly_discount': '0',
            'current_step': '6',
            'gallery_images': [
                make_test_image('photo-a.png'),
                make_test_image('photo-b.png'),
                make_test_image('photo-c.png'),
            ],
            'image_positions': ['north', 'north', 'aerial'],
        }

        response = self.client.post(reverse('lands:add_land'), payload)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Choose different viewing directions for each photo.')
        self.assertFalse(Land.objects.filter(title='Duplicate Positions Plot').exists())

    def test_invalid_publish_keeps_current_step(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse('lands:add_land'),
            {
                'title': 'Invalid Discount Plot',
                'usage': 'rent',
                'land_use': 'residential',
                'price': '500000',
                'price_unit': 'month',
                'region': 'arusha',
                'district': 'Arusha City',
                'ward': 'Sekei',
                'street': 'Njiro Road',
                'size': '2.5',
                'size_unit': 'acres',
                'topography': 'flat',
                'soil_fertility': 'moderate',
                'contact_phone': '0712345678',
                'contact_email': 'wizard-owner@example.com',
                'owner_will_refund': 'True',
                'weekly_discount': '95',
                'monthly_discount': '0',
                'current_step': '6',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="6"')
        self.assertContains(response, 'Must be 0')


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
        self.admin = User.objects.create_user(
            username='admin',
            password='pass12345',
            email='admin@example.com',
            role=User.ROLE_ADMIN,
            is_staff=True,
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
        self.reservation.status = 'awaiting_payment'
        self.reservation.save()
        self.client.force_login(self.customer)

        response = self.client.post(
            reverse('lands:submit_payment', args=[self.reservation.pk]),
            {
                'amount': '500000',
                'payment_method': 'bank',
                'payment_reference': 'ABC123XYZ',
                'payment_date': date.today().isoformat(),
                'notes': 'Paid via transfer',
            },
        )

        self.reservation.refresh_from_db()
        payment = PaymentRecord.objects.get(reservation=self.reservation)
        self.assertRedirects(response, reverse('lands:payments_and_bills'))
        self.assertEqual(self.reservation.status, 'awaiting_payment')
        self.assertEqual(self.reservation.payment_status, 'unpaid')
        self.assertFalse(self.reservation.payment_confirmed)
        self.assertEqual(self.reservation.payment_reference, 'ABC123XYZ')
        self.assertEqual(str(payment.amount), '500000.00')
        self.assertEqual(str(self.reservation.remaining_balance), '500000.00')

    def test_payment_method_selection_redirects_to_submit_payment(self):
        config = OperatorPaymentConfig.objects.create(
            payment_method='bank_transfer',
            account_identifier='0123456789',
            account_holder_name='Land Reserve Ltd',
            priority=1,
            is_active=True,
        )
        self.reservation.status = 'awaiting_payment'
        self.reservation.save()
        self.client.force_login(self.customer)

        response = self.client.post(
            reverse('lands:reservation_payment_options', args=[self.reservation.pk]),
            {'payment_config': str(config.pk)},
        )

        self.reservation.refresh_from_db()
        self.assertRedirects(response, reverse('lands:submit_payment', args=[self.reservation.pk]))
        self.assertEqual(self.reservation.selected_operator_payment, config)
        self.assertEqual(self.reservation.payment_method, 'bank_transfer')

    def test_pending_reservation_payment_method_selection_redirects_to_submit_payment(self):
        config = OperatorPaymentConfig.objects.create(
            payment_method='bank_transfer',
            account_identifier='0123456789',
            account_holder_name='Land Reserve Ltd',
            priority=1,
            is_active=True,
        )
        self.client.force_login(self.customer)

        response = self.client.post(
            reverse('lands:reservation_payment_options', args=[self.reservation.pk]),
            {'payment_config': str(config.pk)},
        )

        self.reservation.refresh_from_db()
        self.assertRedirects(response, reverse('lands:submit_payment', args=[self.reservation.pk]))
        self.assertEqual(self.reservation.selected_operator_payment, config)
        self.assertEqual(self.reservation.payment_method, 'bank_transfer')

    def test_submit_payment_allows_approved_reservation(self):
        self.reservation.status = 'approved'
        self.reservation.save()
        self.client.force_login(self.customer)

        response = self.client.post(
            reverse('lands:submit_payment', args=[self.reservation.pk]),
            {
                'amount': '500000',
                'payment_method': 'bank',
                'payment_reference': 'APPROVED123',
                'payment_date': date.today().isoformat(),
                'notes': 'Approved booking payment',
            },
        )

        self.reservation.refresh_from_db()
        payment = PaymentRecord.objects.get(reservation=self.reservation)
        self.assertRedirects(response, reverse('lands:payments_and_bills'))
        self.assertEqual(self.reservation.status, 'approved')
        self.assertEqual(str(payment.amount), '500000.00')
        self.assertEqual(self.reservation.payment_reference, 'APPROVED123')

    def test_submit_payment_allows_pending_reservation_after_method_selection(self):
        config = OperatorPaymentConfig.objects.create(
            payment_method='mpesa',
            account_identifier='0712000001',
            account_holder_name='Land Reserve Ltd',
            priority=1,
            is_active=True,
        )
        self.reservation.selected_operator_payment = config
        self.reservation.payment_method = config.payment_method
        self.reservation.save()
        self.client.force_login(self.customer)

        response = self.client.post(
            reverse('lands:submit_payment', args=[self.reservation.pk]),
            {
                'amount': '500000',
                'payment_method': 'mpesa',
                'payment_reference': 'PENDING123',
                'payment_date': date.today().isoformat(),
                'notes': 'Pending booking payment',
            },
        )

        self.reservation.refresh_from_db()
        payment = PaymentRecord.objects.get(reservation=self.reservation)
        self.assertRedirects(response, reverse('lands:payments_and_bills'))
        self.assertEqual(self.reservation.status, 'pending')
        self.assertEqual(str(payment.amount), '500000.00')
        self.assertEqual(self.reservation.payment_reference, 'PENDING123')

    def test_refund_request_is_available_for_approved_booking(self):
        self.reservation.status = 'approved'
        self.reservation.save()
        self.client.force_login(self.customer)

        response = self.client.get(reverse('lands:refund_request', args=[self.reservation.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Request Refund')

    def test_refund_request_submits_reason_without_cancelling_booking(self):
        self.reservation.status = 'approved'
        self.reservation.save()
        self.client.force_login(self.customer)

        response = self.client.post(
            reverse('lands:refund_request', args=[self.reservation.pk]),
            {'reason': 'The land no longer meets my project requirements after approval.'},
        )

        self.reservation.refresh_from_db()
        self.assertRedirects(response, reverse('lands:my_bookings'))
        self.assertTrue(self.reservation.refund_requested)
        self.assertIn('project requirements', self.reservation.refund_reason)
        self.assertEqual(self.reservation.status, 'approved')

    def test_approved_booking_cannot_be_cancelled_directly(self):
        self.reservation.status = 'approved'
        self.reservation.save()
        self.client.force_login(self.customer)

        response = self.client.post(reverse('lands:cancel_reservation', args=[self.reservation.pk]))

        self.reservation.refresh_from_db()
        self.assertRedirects(response, reverse('lands:refund_request', args=[self.reservation.pk]))
        self.assertEqual(self.reservation.status, 'approved')
        self.assertFalse(self.reservation.refund_requested)

    def test_payments_dashboard_shows_continue_payment_for_pending_reservation(self):
        self.client.force_login(self.customer)

        response = self.client.get(reverse('lands:payments_and_bills'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Continue payment')

    def test_payments_dashboard_shows_update_reference_when_reference_exists(self):
        config = OperatorPaymentConfig.objects.create(
            payment_method='bank_transfer',
            account_identifier='0123456789',
            account_holder_name='Land Reserve Ltd',
            priority=1,
            is_active=True,
        )
        self.reservation.status = 'awaiting_payment'
        self.reservation.selected_operator_payment = config
        self.reservation.payment_method = config.payment_method
        self.reservation.payment_reference = 'REF-12345'
        self.reservation.save()
        self.client.force_login(self.customer)

        response = self.client.get(reverse('lands:payments_and_bills'), {'booking': self.reservation.pk})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Update reference number')

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
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('lands:confirm_payment_receipt', args=[self.reservation.pk]),
            {'action': 'confirm', 'payment_id': payment.pk},
        )

        self.reservation.refresh_from_db()
        payment.refresh_from_db()
        self.assertRedirects(response, reverse('lands:manage_payments'), fetch_redirect_response=False)
        self.assertFalse(self.reservation.payment_confirmed)
        self.assertEqual(self.reservation.payment_status, 'unpaid')
        self.assertEqual(self.reservation.status, 'awaiting_payment')
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
        self.assertEqual(self.reservation.status, 'awaiting_payment')
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
        self.reservation.status = 'awaiting_payment'
        self.reservation.save()

        self.client.force_login(self.customer)
        response = self.client.post(
            reverse('lands:submit_payment', args=[self.reservation.pk]),
            {
                'amount': '50000',
                'payment_method': 'bank',
                'payment_reference': 'SECOND123',
                'payment_date': date.today().isoformat(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'You must pay the full remaining balance')

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

    def test_owner_dashboard_links_to_refund_requests(self):
        self.reservation.status = 'approved'
        self.reservation.refund_requested = True
        self.reservation.refund_reason = 'Customer wants a different location.'
        self.reservation.save()

        self.client.force_login(self.owner)
        response = self.client.get(reverse('lands:owner_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Refund Requests')
        self.assertContains(response, 'Click to review refund reasons')

    def test_manage_payments_refunds_filter_shows_refund_reason(self):
        self.reservation.status = 'approved'
        self.reservation.refund_requested = True
        self.reservation.refund_reason = 'Customer wants a different location.'
        self.reservation.save()

        self.client.force_login(self.owner)
        response = self.client.get(reverse('lands:manage_payments'), {'payment': 'refunds'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Refunds')
        self.assertContains(response, 'Refund request submitted')
        self.assertContains(response, 'Customer wants a different location.')
