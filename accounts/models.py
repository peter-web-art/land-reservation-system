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

class PaymentDetails(AuditBase):
    """
    Stores owner's payment details for receiving fund payouts.
    Used when admin releases escrowed funds to land owners.
    """
    PAYMENT_METHOD_CHOICES = [
        ('mpesa', 'M-Pesa'),
        ('airtel', 'Airtel Money'),
        ('tigo', 'Tigo Money'),
        ('bank_transfer', 'Bank Transfer'),
        ('bank_cheque', 'Bank Cheque'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='payment_details')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='mpesa',
                                     help_text='Preferred payment method for receiving payouts')
    account_identifier = models.CharField(max_length=100, blank=True,
                                         help_text='M-Pesa number, bank account number, etc.')
    account_holder_name = models.CharField(max_length=200, blank=True,
                                          help_text='Name associated with the payment account')
    bank_name = models.CharField(max_length=100, blank=True,
                                help_text='Bank name (if applicable)')
    bank_branch = models.CharField(max_length=100, blank=True,
                                  help_text='Bank branch (if applicable)')
    is_verified = models.BooleanField(default=False,
                                     help_text='Admin has verified these payment details')
    verified_on = models.DateTimeField(null=True, blank=True)
    is_default = models.BooleanField(default=True,
                                    help_text='Use as default for payouts')

    class Meta:
        verbose_name_plural = "Payment Details"

    def __str__(self):
        return f"Payment details for {self.user.username} ({self.get_payment_method_display()})"

class OperatorPaymentConfig(AuditBase):
    """
    Stores payment details configured by admin/operator for customers to use.
    This is where customers should send their payments.
    """
    PAYMENT_METHOD_CHOICES = [
        ('mpesa', 'M-Pesa'),
        ('airtel', 'Airtel Money'),
        ('tigo', 'Tigo Money'),
        ('bank_transfer', 'Bank Transfer'),
        ('bank_cheque', 'Bank Cheque'),
    ]
    
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES,
                                     unique=True,
                                     help_text='Payment method customers should use')
    account_identifier = models.CharField(max_length=100,
                                         help_text='M-Pesa number, bank account, etc. where customers pay')
    account_holder_name = models.CharField(max_length=200,
                                          help_text='Business/operator name')
    bank_name = models.CharField(max_length=100, blank=True,
                                help_text='Bank name (if applicable)')
    bank_branch = models.CharField(max_length=100, blank=True,
                                  help_text='Bank branch (if applicable)')
    instructions = models.TextField(blank=True,
                                   help_text='Payment instructions to display to customers')
    is_active = models.BooleanField(default=True,
                                   help_text='Whether this payment method is available')
    priority = models.PositiveIntegerField(default=0,
                                          help_text='Display order (0 = highest priority)')

    class Meta:
        verbose_name_plural = "Operator Payment Config"
        ordering = ['priority', '-created_on']

    def __str__(self):
        return f"{self.get_payment_method_display()} - {self.account_identifier}"

class SystemSettings(models.Model):
    maintenance_mode = models.BooleanField(default=False)
    email_notifications = models.BooleanField(default=True)
    platform_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('5.00'))
    last_backup = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "System Settings"

    def __str__(self):
        return "Global System Settings"
