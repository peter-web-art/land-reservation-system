from django.db import models
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
from accounts.models import User, AuditBase


class Utility(AuditBase):
    """Specific utilities or amenities available on the land"""
    name = models.CharField(max_length=100, unique=True)
    land = models.ForeignKey('Land', on_delete=models.CASCADE, related_name='utility_records', null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    icon_class = models.CharField(max_length=50, blank=True, null=True, help_text="CSS icon class (e.g., FontAwesome)")

    class Meta:
        verbose_name_plural = "Utilities"
        ordering = ['name']

    def __str__(self):
        return self.name





class Land(AuditBase):
    land_id = models.CharField(max_length=20, unique=True, null=True, blank=True,
                               help_text='Unique reference ID (e.g. LR-001)')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lands')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)

    # ── STRUCTURED LOCATION (Tanzania) ────────────────────────────────────────
    from lands.tanzania_locations import REGION_CHOICES as _REGION_CHOICES
    region = models.CharField(max_length=30, choices=_REGION_CHOICES, blank=True,
                              help_text='Mkoa')
    district = models.CharField(max_length=100, blank=True,
                                help_text='Wilaya')
    ward = models.CharField(max_length=100, blank=True,
                            help_text='Kata')
    street = models.CharField(max_length=100, blank=True,
                              help_text='Mtaa / Kijiji')
    # Legacy free-text field — auto-populated from structured fields on save
    location = models.CharField(max_length=200, blank=True)

    latitude = models.FloatField(null=True, blank=True, help_text='GPS latitude for map pin')
    longitude = models.FloatField(null=True, blank=True, help_text='GPS longitude for map pin')

    USAGE_CHOICES = [('rent', 'Rent'), ('sale', 'Sale')]
    usage = models.CharField(max_length=10, choices=USAGE_CHOICES, default='rent')

    SIZE_UNIT_CHOICES = [('acres', 'Acres'), ('hectares', 'Hectares'), ('sqm', 'Sq. Metres')]
    size = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    size_unit = models.CharField(max_length=10, choices=SIZE_UNIT_CHOICES, default='acres', blank=True)

    LAND_TYPE_CHOICES = [
        ('agricultural', 'Agricultural'), ('residential', 'Residential'),
        ('commercial', 'Commercial'), ('industrial', 'Industrial'), ('mixed', 'Mixed Use'),
    ]
    land_use = models.CharField(max_length=20, choices=LAND_TYPE_CHOICES, default='agricultural', blank=True)

    # ── TERRAIN & UTILITIES ───────────────────────────────────────────────────
    TOPOGRAPHY_CHOICES = [
        ('flat', 'Flat'), ('sloped', 'Sloped'), ('rolling', 'Rolling Hills'),
        ('mountainous', 'Mountainous'), ('depressed', 'Depressed/Lowland'),
    ]
    topography = models.CharField(max_length=20, choices=TOPOGRAPHY_CHOICES, default='flat', blank=True)

    SOIL_FERTILITY_CHOICES = [
        ('very_low', 'Very Low — Degraded / Sandy'),
        ('low', 'Low — Needs Improvement'),
        ('moderate', 'Moderate — Average'),
        ('high', 'High — Fertile'),
        ('very_high', 'Very High — Rich Volcanic / Alluvial'),
    ]
    soil_fertility = models.CharField(
        max_length=20, choices=SOIL_FERTILITY_CHOICES, default='moderate', blank=True,
        help_text='Soil fertility level — used for automatic crop suggestions'
    )

    # ── UTILITIES & AMENITIES ────────────────────────────────────────────────
    utilities = models.ManyToManyField(Utility, related_name='lands', blank=True,
                help_text='Select all available utilities and improvements')
    additional_utilities_notes = models.TextField(blank=True, null=True,
                help_text='Additional notes on utilities not mentioned above')


    # ── AIRBNB-STYLE PRICING ───────────────────────────────────────────────────
    PRICE_UNIT_CHOICES = [
        ('month', 'Per Month'),
        ('year',  'Per Year'),
        ('total', 'Total / One-time'),
    ]
    price      = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text='Base price')
    price_unit = models.CharField(max_length=10, choices=PRICE_UNIT_CHOICES, default='month', blank=True)

    # Discount rates (Airbnb-style)
    weekly_discount  = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                        help_text='% discount for bookings of 1+ week (rent only)')
    monthly_discount = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                        help_text='% discount for bookings of 1+ month (rent only)')

    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    land_image_path = models.ImageField(upload_to='lands/', blank=True, null=True)
    is_active     = models.BooleanField(default=True)
    is_draft      = models.BooleanField(default=False, help_text='Whether this land listing is a draft')
    wizard_step   = models.PositiveIntegerField(default=1, help_text='The current step in the registration wizard')
    view_count    = models.PositiveIntegerField(default=0, help_text='Number of detail page views')

    def save(self, *args, **kwargs):
        # Auto-generate land_id if not provided
        if not self.land_id:
            # Generate unique land reference like LR-001, LR-002, etc.
            last_land = Land.objects.order_by('-id').first()
            if last_land and last_land.land_id and last_land.land_id.startswith('LR-'):
                try:
                    last_num = int(last_land.land_id[3:])
                    self.land_id = f'LR-{last_num + 1:03d}'
                except ValueError:
                    self.land_id = 'LR-001'
            else:
                self.land_id = 'LR-001'
        
        # Auto-build the location string from structured fields
        if self.region:
            from lands.tanzania_locations import build_full_location
            self.location = build_full_location(
                self.region, self.district, self.ward, self.street
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def is_available_for_dates(self, start_date=None, end_date=None, requested_size=None):
        """
        Check if the land has enough remaining size available for the requested dates.
        If requested_size is None, checks if there's any availability at all.
        """
        remaining = self.get_remaining_size_for_dates(start_date, end_date)
        if remaining <= 0:
            return False
        if requested_size and remaining < requested_size:
            return False
        return True

    def get_remaining_size_for_dates(self, start_date=None, end_date=None):
        """Calculates how much size is currently unbooked for a given period."""
        if not self.size:
            # If land size isn't specified, assume it's a single unit (1 whole).
            # If any booking exists without a size, it takes the whole unit.
            total = Decimal('1')
        else:
            total = self.size

        if self.usage == 'sale':
            # Sum all approved and pending sales to avoid overselling
            sales = self.reservations.filter(status__in=['approved', 'pending'])
            booked = Decimal('0')
            for s in sales:
                if s.requested_size is None:
                    # If any sale is for the whole land, it's fully booked.
                    return Decimal('0')
                booked += s.requested_size
            return max(Decimal('0'), total - booked)
        
        # For rent
        if not start_date or not end_date:
            start_date = date.today()
            end_date = start_date + timedelta(days=1)
            
        overlaps = self.reservations.filter(
            status__in=['approved', 'pending'],
            start_date__lt=end_date,
            end_date__gt=start_date
        )
        
        if not overlaps.exists():
            return total
            
        # Check day by day for maximum concurrent usage
        current = start_date
        max_booked = Decimal('0')
        while current < end_date:
            daily_booked = Decimal('0')
            for res in overlaps:
                if res.start_date <= current < res.end_date:
                    if res.requested_size is None:
                        return Decimal('0')
                    daily_booked += res.requested_size
            if daily_booked > max_booked:
                max_booked = daily_booked
            current += timedelta(days=1)
            
        return max(Decimal('0'), total - max_booked)

    @property
    def current_remaining_size(self):
        """Returns the currently available size starting today."""
        # Force fresh calculation from database
        if self.usage == 'sale':
            return self.get_remaining_size_for_dates()
        return self.get_remaining_size_for_dates(date.today(), date.today() + timedelta(days=1))

    @property
    def has_approved_reservations(self):
        """Checks if the land has any approved reservations (active or future)."""
        return self.reservations.filter(status='approved').exists()

    @property
    def is_available(self):
        """
        Land is 'Available' if it has at least some space today.
        Matches 'Normal Booking' logic.
        """
        return self.current_remaining_size > 0

    @property
    def is_reserved(self):
        """Land is 'Reserved' if it has any approved reservations at all."""
        return self.has_approved_reservations

    def get_active_reservation(self):
        """Returns the first active reservation (for UI display when fully booked)."""
        today = date.today()
        return self.reservations.filter(status='approved', end_date__gte=today).order_by('start_date').first()

    def get_booked_periods(self):
        """Returns periods where the land is completely fully booked (0 size remaining)."""
        today = date.today()
        # To strictly do this, we'd have to find periods where sum == total.
        # For UI simplicity, let's just return periods where at least something is booked,
        # but mark if it's 'full' or 'partial'.
        # However, to avoid breaking existing UI, let's return bookings that take the WHOLE land,
        # or if it's partially booked, it's technically still available.
        # To not overcomplicate, we'll return all bookings with their requested sizes.
        return list(
            self.reservations.filter(
                status__in=['approved', 'pending'],
                start_date__isnull=False,
                end_date__isnull=False,
                end_date__gte=today,
            ).order_by('start_date').values('start_date', 'end_date', 'status', 'requested_size')
        )

    @property
    def next_available_date(self):
        """Finds the next date where at least some size is available."""
        today = date.today()
        if self.get_remaining_size_for_dates(today, today + timedelta(days=1)) > 0:
            return today
            
        booked = self.reservations.filter(
            status__in=['approved', 'pending'],
            end_date__gte=today,
        ).order_by('end_date')
        
        # Check the day after each booking ends to see if space frees up
        for res in booked:
            check_date = res.end_date + timedelta(days=1)
            if self.get_remaining_size_for_dates(check_date, check_date + timedelta(days=1)) > 0:
                return check_date
        return today

    @property
    def price_display(self):
        if self.price is None:
            return 'Price not set'
        unit_map = {'month': '/month', 'year': '/year', 'total': ''}
        suffix = unit_map.get(self.price_unit, '')
        return f'Tsh {self.price:,.0f}{suffix}'

    @property
    def get_all_images(self):
        """Get all images for this land from LandImage model, fallback to legacy field."""
        images = list(self.images.all().order_by('order', 'id'))
        if images:
            return images
        # Fallback to legacy single-image field
        return [self.land_image_path] if self.land_image_path else []

    @property
    def primary_image(self):
        """Get the primary/cover image for this land."""
        primary = self.images.filter(is_primary=True).first()
        if primary:
            return primary.image
        first = self.images.first()
        if first:
            return first.image
        return self.land_image_path

    @property
    def image_count(self):
        """Total number of images uploaded."""
        count = self.images.count()
        if count == 0 and self.land_image_path:
            return 1
        return count

    def calculate_price(self, start_date, end_date):
        """Calculate total price for a date range, applying discounts."""
        if self.price is None:
            return None
        if self.usage == 'sale' or not start_date or not end_date:
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


class LandImage(AuditBase):
    """Individual image for a land listing with position/direction metadata."""
    POSITION_CHOICES = [
        ('north', 'North View'),
        ('south', 'South View'),
        ('east', 'East View'),
        ('west', 'West View'),
        ('aerial', 'Aerial View'),
        ('from_above', 'From Above'),
        ('vertical', 'Vertical View'),
        ('horizontal', 'Horizontal / Panoramic'),
        ('front', 'Front View'),
        ('other', 'Other'),
    ]

    land = models.ForeignKey(Land, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='lands/gallery/')
    position = models.CharField(max_length=20, choices=POSITION_CHOICES, default='other',
                                help_text='Direction / angle from which the photo was taken')
    caption = models.CharField(max_length=200, blank=True,
                               help_text='Optional short description of this photo')
    is_primary = models.BooleanField(default=False,
                                     help_text='Use as the cover / thumbnail image')
    order = models.PositiveIntegerField(default=0, help_text='Display order (lower = first)')

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Land Image'
        verbose_name_plural = 'Land Images'

    def __str__(self):
        return f"{self.land.title} — {self.get_position_display()}"

    def save(self, *args, **kwargs):
        # If this is marked primary, un-mark any other primary images for the same land
        if self.is_primary:
            LandImage.objects.filter(land=self.land, is_primary=True).exclude(pk=self.pk).update(is_primary=False)
        # If this is the first image for the land, auto-mark as primary
        if not self.pk and not LandImage.objects.filter(land=self.land).exists():
            self.is_primary = True
        super().save(*args, **kwargs)


class Reservation(AuditBase):
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

    # Date range (for rent bookings)
    start_date = models.DateField(null=True, blank=True, help_text='Start date of rental period')
    end_date   = models.DateField(null=True, blank=True, help_text='End date of rental period')

    status         = models.CharField(max_length=20, choices=RESERVATION_STATUS, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='unpaid')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD, blank=True, null=True)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    payment_receipt   = models.ImageField(upload_to='payments/receipts/', blank=True, null=True, help_text='Upload proof of payment (screenshot/receipt)')
    payment_date      = models.DateField(null=True, blank=True, help_text='Date when payment was made')
    payment_confirmed = models.BooleanField(default=False, help_text='True if owner has confirmed receipt of funds')
    amount_paid    = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    agreed_price   = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                      help_text='Final agreed price for this booking')
    requested_size = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                      help_text='Size requested by customer (if partial)')
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
    def release_status(self):
        if self.status == 'approved' and self.end_date:
            remaining = (self.end_date - date.today()).days
            if remaining > 0:
                return f'{remaining} day{"s" if remaining != 1 else ""} until release'
            if remaining == 0:
                return 'Release today'
            return 'Release overdue'
        return None

    @property
    def total_amount(self):
        if self.agreed_price:
            return self.agreed_price
        if self.start_date and self.end_date:
            return self.land.calculate_price(self.start_date, self.end_date)
        return self.land.price

    @property
    def confirmed_amount_total(self):
        if self.payments.exists():
            return sum(
                (payment.amount or Decimal('0'))
                for payment in self.payments.filter(status='confirmed')
            )
        confirmed_total = sum(
            (payment.amount or Decimal('0'))
            for payment in self.payments.filter(status='confirmed')
        )
        legacy_total = self.amount_paid or Decimal('0')
        return confirmed_total + legacy_total

    @property
    def submitted_amount_total(self):
        if self.payments.exists():
            return sum(
                (payment.amount or Decimal('0'))
                for payment in self.payments.filter(status__in=['submitted', 'confirmed'])
            )
        submitted_total = sum(
            (payment.amount or Decimal('0'))
            for payment in self.payments.filter(status__in=['submitted', 'confirmed'])
        )
        legacy_total = self.amount_paid or Decimal('0')
        return submitted_total + legacy_total

    @property
    def remaining_balance(self):
        total = self.total_amount or Decimal('0')
        remaining = total - self.confirmed_amount_total
        return max(Decimal('0'), remaining)

    @property
    def pending_payment_total(self):
        return sum(
            (payment.amount or Decimal('0'))
            for payment in self.payments.filter(status='submitted')
        )

    @property
    def platform_fee_total(self):
        if self.payments.exists():
            return sum(
                (payment.platform_fee_amount or Decimal('0'))
                for payment in self.payments.filter(status='confirmed')
            )
        return Decimal('0')

    @property
    def owner_net_total(self):
        return max(Decimal('0'), self.confirmed_amount_total - self.platform_fee_total)

    @property
    def latest_pending_payment(self):
        return self.payments.filter(status='submitted').order_by('-created_on').first()

    @property
    def payment_review_status(self):
        if self.remaining_balance <= 0:
            return 'confirmed'
        if self.payments.filter(status='submitted').exists() or self.payment_reference:
            return 'submitted'
        return 'pending'

    @property
    def is_fully_paid(self):
        return self.remaining_balance <= 0


class PaymentRecord(AuditBase):
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected'),
    ]

    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=Reservation.PAYMENT_METHOD, blank=True, null=True)
    payment_reference = models.CharField(max_length=100)
    payment_receipt = models.ImageField(upload_to='payments/receipts/', blank=True, null=True)
    payment_date = models.DateField(help_text='Date when this installment was paid')
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    platform_fee_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    platform_fee_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    confirmed_on = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_on']

    def __str__(self):
        return f"{self.reservation} - {self.amount} ({self.status})"

    @property
    def owner_net_amount(self):
        fee = self.platform_fee_amount or Decimal('0')
        return max(Decimal('0'), (self.amount or Decimal('0')) - fee)


class Wishlist(AuditBase):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist')
    land = models.ForeignKey(Land, on_delete=models.CASCADE, related_name='wishlisted_by')

    class Meta:
        unique_together = ('user', 'land')
        ordering = ['-created_on']

    def __str__(self):
        return f"{self.user.username} -> {self.land.title}"


class Message(AuditBase):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    land = models.ForeignKey(Land, on_delete=models.CASCADE, related_name='messages', null=True, blank=True)
    subject = models.CharField(max_length=200, blank=True)
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_on']

    def __str__(self):
        return f"{self.sender.username} → {self.recipient.username}: {self.subject or '(no subject)'}"


class Notification(AuditBase):
    NOTIFICATION_TYPES = [
        ('booking_new', 'New Booking'),
        ('booking_approved', 'Booking Approved'),
        ('booking_rejected', 'Booking Rejected'),
        ('booking_cancelled', 'Booking Cancelled'),
        ('payment_received', 'Payment Received'),
        ('message_received', 'New Message'),
        ('payment', 'Payment Update'),
        ('system', 'System Notification'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=200, blank=True, help_text='URL to navigate to when clicked')
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_on']

    def __str__(self):
        return f"{self.user.username} - {self.title}"
