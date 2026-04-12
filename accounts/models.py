from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CUSTOMER = 'customer'
    ROLE_OWNER    = 'owner'
    ROLE_ADMIN    = 'admin'
    ROLE_CHOICES  = [
        (ROLE_CUSTOMER, 'Customer'),
        (ROLE_OWNER,    'Land Owner'),
        (ROLE_ADMIN,    'Admin'),
    ]
    role            = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CUSTOMER)
    is_owner        = models.BooleanField(default=False)
    is_verified     = models.BooleanField(default=False, help_text="Owner verified by admin — no scam risk")
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    phone           = models.CharField(max_length=20, blank=True)
    bio             = models.TextField(blank=True)
    is_suspended    = models.BooleanField(default=False, help_text="Suspended users cannot log in")
    # KYC / Proof of Ownership
    kyc_document    = models.FileField(upload_to='kyc/', blank=True, null=True,
                        help_text="ID / Land title / ownership proof document")
    ownership_proof = models.FileField(upload_to='kyc/ownership/', blank=True, null=True,
                        help_text="Separate land title or ownership proof document")
    kyc_status      = models.CharField(max_length=20, default='not_submitted',
                        choices=[('not_submitted','Not Submitted'),('pending','Pending Review'),
                                 ('approved','Approved'),('rejected','Rejected')])
    kyc_notes       = models.TextField(blank=True, help_text="Admin notes on KYC review")
    # Barua ya Serikali za Mtaa
    govt_letter      = models.FileField(upload_to='kyc/govt_letters/', blank=True, null=True)
    govt_letter_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
