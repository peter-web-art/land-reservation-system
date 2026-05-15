from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from decimal import Decimal

class AuditBase(models.Model):
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="%(class)s_created")
    created_on = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="%(class)s_updated")
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class User(AbstractUser, AuditBase):
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
    is_suspended    = models.BooleanField(default=False, help_text="Suspended users cannot log in")

    @property
    def profile_picture(self):
        personal = getattr(self, 'personal_details', None)
        return getattr(personal, 'photo_path', None)

    @property
    def phone(self):
        personal = getattr(self, 'personal_details', None)
        return getattr(personal, 'phone', '')

    @property
    def bio(self):
        personal = getattr(self, 'personal_details', None)
        return getattr(personal, 'bio', '')

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    class Meta:
        db_table = 'users'
        ordering = ['-created_on']

class PersonalDetails(AuditBase):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='personal_details')
    fname = models.CharField(max_length=100, verbose_name="First Name")
    mname = models.CharField(max_length=100, blank=True, verbose_name="Middle Name")
    surname = models.CharField(max_length=100, verbose_name="Surname")
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    photo_path = models.ImageField(upload_to='personal_photos/', blank=True, null=True)
    bio = models.TextField(blank=True, verbose_name="Bio")

    def __str__(self):
        return f"Details for {self.user.username}"

class SystemSettings(models.Model):
    maintenance_mode = models.BooleanField(default=False)
    email_notifications = models.BooleanField(default=True)
    platform_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('5.00'))
    last_backup = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "System Settings"

    def __str__(self):
        return "Global System Settings"
