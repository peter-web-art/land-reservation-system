from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from .models import Land, Reservation


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
            listing_type='rent',
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
