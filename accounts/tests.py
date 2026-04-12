from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import User


class AccountKycTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='owner1',
            password='pass12345',
            email='owner@example.com',
            role=User.ROLE_OWNER,
            is_owner=True,
        )
        self.client.force_login(self.user)

    def test_submit_kyc_saves_ownership_proof(self):
        id_doc = SimpleUploadedFile(
            'id.pdf',
            b'%PDF-1.4 test document',
            content_type='application/pdf',
        )
        ownership_doc = SimpleUploadedFile(
            'title.pdf',
            b'%PDF-1.4 ownership proof',
            content_type='application/pdf',
        )
        govt_doc = SimpleUploadedFile(
            'letter.pdf',
            b'%PDF-1.4 government letter',
            content_type='application/pdf',
        )

        response = self.client.post(
            reverse('accounts:submit_kyc'),
            {
                'govt_letter_date': '2026-04-01',
                'kyc_document': id_doc,
                'ownership_proof': ownership_doc,
                'govt_letter': govt_doc,
            },
        )

        self.assertRedirects(response, reverse('accounts:profile_edit'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.kyc_status, 'pending')
        self.assertTrue(bool(self.user.kyc_document))
        self.assertTrue(bool(self.user.ownership_proof))
        self.assertTrue(bool(self.user.govt_letter))
