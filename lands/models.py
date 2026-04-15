from django.db import models
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
from accounts.models import User


class LandImage(models.Model):
    """Multiple images per land listing - Airbnb style gallery"""
    land = models.ForeignKey('Land', on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='lands/gallery/')
    caption = models.CharField(max_length=200, blank=True, help_text='Optional caption')
    is_primary = models.BooleanField(default=False, help_text='Set as primary/cover image')
    order = models.PositiveIntegerField(default=0, help_text='Display order')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', '-is_primary', 'created_at']

    def __str__(self):
        return f"{self.land.title} - Image {self.order}"


class Land(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lands')
    title = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=200)
    latitude = models.FloatField(null=True, blank=True, help_text='GPS latitude for map pin')
    longitude = models.FloatField(null=True, blank=True, help_text='GPS longitude for map pin')

    LISTING_CHOICES = [('rent', 'Rent'), ('sale', 'Sale')]
    listing_type = models.CharField(max_length=10, choices=LISTING_CHOICES, default='rent')

    SIZE_UNIT_CHOICES = [('acres', 'Acres'), ('hectares', 'Hectares'), ('sqm', 'Sq. Metres')]
    size = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    size_unit = models.CharField(max_length=10, choices=SIZE_UNIT_CHOICES, default='acres', blank=True)

    LAND_TYPE_CHOICES = [
        ('agricultural', 'Agricultural'), ('residential', 'Residential'),
        ('commercial', 'Commercial'), ('industrial', 'Industrial'), ('mixed', 'Mixed Use'),
    ]
    land_use = models.CharField(max_length=20, choices=LAND_TYPE_CHOICES, default='agricultural', blank=True)

    # ── AIRBNB-STYLE PRICING ───────────────────────────────────────────────────
    PRICE_UNIT_CHOICES = [
        ('month', 'Per Month'),
        ('year',  'Per Year'),
        ('total', 'Total / One-time'),
    ]
    price      = models.DecimalField(max_digits=12, decimal_places=2, help_text='Base price')
    price_unit = models.CharField(max_length=10, choices=PRICE_UNIT_CHOICES, default='month', blank=True)

    # Discount rates (Airbnb-style)
    weekly_discount  = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                        help_text='% discount for bookings of 1+ week (rent only)')
    monthly_discount = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                        help_text='% discount for bookings of 1+ month (rent only)')

    # Minimum/maximum rental duration (rent only)
    min_duration_days = models.PositiveIntegerField(default=1,
                         help_text='Minimum rental period in days (rent listings only)')
    max_duration_days = models.PositiveIntegerField(null=True, blank=True,
                         help_text='Maximum rental period in days (leave blank for no limit)')

    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    image         = models.ImageField(upload_to='lands/', blank=True, null=True)
    is_active     = models.BooleanField(default=True)
    created_at    = models.DateTimeField(auto_now_add=True, null=True)
    view_count    = models.PositiveIntegerField(default=0, help_text='Number of detail page views')

    def __str__(self):
        return self.title

    def is_available_for_dates(self, start, end):
        """Check no approved OR pending reservation overlaps the given date range.
        FIX #9: pending bookings also block dates so two customers cannot
        simultaneously hold overlapping date ranges.
        """
        if not start or not end:
            return True
        return not self.reservations.filter(
            status__in=['approved', 'pending'],
            start_date__isnull=False,
            end_date__isnull=False,
            start_date__lt=end,
            end_date__gt=start
        ).exists()

    @property
    def is_available(self):
        if self.listing_type == 'sale':
            return not self.reservations.filter(status='approved').exists()
        today = date.today()
        return not self.reservations.filter(
            status='approved', end_date__gte=today).exists()

    @property
    def status_display(self):
        return "Available" if self.is_available else "Booked"

    @property
    def price_display(self):
        unit_map = {'month': '/month', 'year': '/year', 'total': ''}
        suffix = unit_map.get(self.price_unit, '')
        return f'${self.price:,.0f}{suffix}'

    @property
    def get_all_images(self):
        """Get all images for this land (gallery + main image), deduplicated"""
        gallery_images = list(self.images.all())
        result = []
        # Add main image first if it exists
        if self.image:
            result.append(self.image)
        # Add gallery images, skipping any that match the main image
        for img in gallery_images:
            if not self.image or img.image.name != self.image.name:
                result.append(img.image)
        return result if result else []

    @property
    def primary_image(self):
        """Get the primary/cover image for this land"""
        primary = self.images.filter(is_primary=True).first()
        if primary:
            return primary.image
        return self.image

    def calculate_price(self, start_date, end_date):
        """Calculate total price for a date range, applying discounts."""
        if self.listing_type == 'sale' or not start_date or not end_date:
            return self.price
        days = (end_date - start_date).days
        if days <= 0:
            return self.price
        # Calculate base cost
        if self.price_unit == 'month':
            months = days / 30
            base = self.price * Decimal(str(months))
        elif self.price_unit == 'year':
            years = days / 365
            base = self.price * Decimal(str(years))
        else:
            base = self.price
        # Apply discounts
        weeks = days / 7
        if weeks >= 4 and self.monthly_discount > 0:
            discount = self.monthly_discount / 100
        elif weeks >= 1 and self.weekly_discount > 0:
            discount = self.weekly_discount / 100
        else:
            discount = Decimal('0')
        total = base * (1 - discount)
        return round(total, 2)


class Reservation(models.Model):
    RESERVATION_STATUS = [
        ('pending', 'Pending'), ('approved', 'Approved'),
        ('rejected', 'Rejected'), ('cancelled', 'Cancelled'),
    ]
    PAYMENT_STATUS = [
        ('unpaid', 'Unpaid'), ('paid', 'Paid'), ('refunded', 'Refunded'),
    ]
    PAYMENT_METHOD = [
        ('mpesa', 'M-Pesa'), ('airtel', 'Airtel Money'), ('tigopesa', 'Tigo Pesa'),
        ('bank', 'Bank Transfer'), ('cash', 'Cash on Arrival'),
    ]

    land           = models.ForeignKey(Land, on_delete=models.CASCADE, related_name='reservations')
    customer       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reservations', null=True, blank=True)
    customer_name  = models.CharField(max_length=100, blank=True)
    customer_email = models.EmailField(blank=True)
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    booking_date   = models.DateTimeField(auto_now_add=True)

    # Date range (for rent bookings)
    start_date = models.DateField(null=True, blank=True, help_text='Start date of rental period')
    end_date   = models.DateField(null=True, blank=True, help_text='End date of rental period')

    status         = models.CharField(max_length=20, choices=RESERVATION_STATUS, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='unpaid')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD, blank=True, null=True)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    amount_paid    = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    agreed_price   = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                      help_text='Final agreed price for this booking')
    notes          = models.TextField(blank=True)

    class Meta:
        # BUG #2 FIX: Add database indexes for faster queries on common filters
        indexes = [
            models.Index(fields=['land', 'status', 'start_date', 'end_date']),
            models.Index(fields=['land', 'customer']),
            models.Index(fields=['customer_email']),
        ]

    def __str__(self):
        name = self.customer.username if self.customer else self.customer_name
        return f"{name} — {self.land.title}"

    @property
    def duration_days(self):
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days
        return None

    @property
    def duration_display(self):
        days = self.duration_days
        if not days:
            return '—'
        if days >= 365:
            return f'{days // 365}yr {(days % 365) // 30}mo'
        if days >= 30:
            return f'{days // 30} month{"s" if days // 30 != 1 else ""}'
        if days >= 7:
            return f'{days // 7} week{"s" if days // 7 != 1 else ""}'
        return f'{days} day{"s" if days != 1 else ""}'

    @property
    def total_amount(self):
        if self.agreed_price:
            return self.agreed_price
        if self.start_date and self.end_date:
            return self.land.calculate_price(self.start_date, self.end_date)
        return self.land.price


class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist')
    land = models.ForeignKey(Land, on_delete=models.CASCADE, related_name='wishlisted_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'land')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} -> {self.land.title}"


class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    land = models.ForeignKey(Land, on_delete=models.CASCADE, related_name='messages', null=True, blank=True)
    subject = models.CharField(max_length=200, blank=True)
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.sender.username} → {self.recipient.username}: {self.subject or '(no subject)'}"


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('booking_new', 'New Booking'),
        ('booking_approved', 'Booking Approved'),
        ('booking_rejected', 'Booking Rejected'),
        ('booking_cancelled', 'Booking Cancelled'),
        ('payment_received', 'Payment Received'),
        ('message_received', 'New Message'),
        ('kyc_status', 'KYC Status Update'),
        ('system', 'System Notification'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=200, blank=True, help_text='URL to navigate to when clicked')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"
