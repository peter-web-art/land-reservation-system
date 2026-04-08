from django.contrib import admin
from django.utils.html import format_html
from .models import Land, Reservation, LandImage


class LandImageInline(admin.TabularInline):
    model = LandImage
    extra = 1
    fields = ['image', 'caption', 'is_primary', 'order']
    readonly_fields = ['created_at']


@admin.register(Land)
class LandAdmin(admin.ModelAdmin):
    list_display  = ('title', 'owner_display', 'location', 'listing_type',
                     'price_display', 'land_use', 'availability', 'is_active', 'reservation_count')
    list_filter   = ('listing_type', 'land_use', 'is_active')
    search_fields = ('title', 'location', 'owner__username', 'owner__email')
    ordering      = ('-created_at',)
    readonly_fields = ('reservation_count',)
    list_editable  = ('is_active',)
    inlines = [LandImageInline]
    actions = ['delete_selected']  # Enable bulk delete from admin
    fieldsets = (
        ('Basic',   {'fields': ('title', 'description', 'owner', 'is_active')}),
        ('Location & Type', {'fields': ('location', 'latitude', 'longitude', 'listing_type', 'land_use', 'size', 'size_unit')}),
        ('Pricing', {'fields': ('price', 'price_unit', 'weekly_discount', 'monthly_discount',
                                'min_duration_days', 'max_duration_days')}),
        ('Contact', {'fields': ('contact_phone', 'contact_email', 'image')}),
    )

    def owner_display(self, obj):
        v = ' ✔' if obj.owner.is_verified else ''
        return format_html('{}{}', obj.owner.username, v)
    owner_display.short_description = 'Owner'

    def price_display(self, obj):
        return obj.price_display
    price_display.short_description = 'Price'

    def availability(self, obj):
        if obj.is_available:
            return format_html('<span style="color:#1e5229;font-weight:600;">✔ Available</span>')
        return format_html('<span style="color:#c0392b;font-weight:600;">✘ Booked</span>')
    availability.short_description = 'Availability'

    def reservation_count(self, obj):
        return obj.reservations.count()
    reservation_count.short_description = '# Bookings'


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display  = ('land_title', 'customer_display', 'customer_phone',
                     'start_date', 'end_date', 'duration_display',
                     'agreed_price_display', 'status_badge',
                     'payment_status_badge', 'booking_date')
    list_filter   = ('status', 'payment_status', 'payment_method')
    search_fields = ('land__title', 'customer__username', 'customer_name',
                     'customer_email', 'customer_phone', 'payment_reference')
    ordering      = ('-booking_date',)
    readonly_fields = ('booking_date', 'agreed_price', 'duration_display')
    actions       = ['approve_reservations', 'reject_reservations']
    fieldsets = (
        ('Booking', {'fields': ('land', 'customer', 'customer_name', 'customer_email',
                                'customer_phone', 'status', 'notes')}),
        ('Dates',   {'fields': ('start_date', 'end_date', 'booking_date')}),
        ('Payment', {'fields': ('agreed_price', 'payment_status', 'payment_method',
                                'payment_reference', 'amount_paid')}),
    )

    def land_title(self, obj): return obj.land.title
    land_title.short_description = 'Land'

    def customer_display(self, obj):
        return obj.customer.username if obj.customer else (obj.customer_name or '—')
    customer_display.short_description = 'Customer'

    def agreed_price_display(self, obj):
        p = obj.agreed_price or obj.land.price
        return format_html('<strong>${:,.0f}</strong>', p)
    agreed_price_display.short_description = 'Price'

    def duration_display(self, obj):
        return obj.duration_display
    duration_display.short_description = 'Duration'

    def status_badge(self, obj):
        colors = {'pending': '#d4811a', 'approved': '#1e5229',
                  'rejected': '#c0392b', 'cancelled': '#888'}
        c = colors.get(obj.status, '#555')
        return format_html('<span style="color:{};font-weight:600;">{}</span>',
                           c, obj.get_status_display())
    status_badge.short_description = 'Status'

    def payment_status_badge(self, obj):
        if obj.payment_status == 'paid':
            return format_html('<span style="color:#1e5229;font-weight:600;">✔ Paid</span>')
        if obj.payment_status == 'refunded':
            return format_html('<span style="color:#1a5276;">↩ Refunded</span>')
        return format_html('<span style="color:#d4811a;">Unpaid</span>')
    payment_status_badge.short_description = 'Payment'

    @admin.action(description='✔ Approve selected reservations')
    def approve_reservations(self, request, queryset):
        updated = queryset.update(status='approved')
        self.message_user(request, f'{updated} approved.')

    @admin.action(description='✘ Reject selected reservations')
    def reject_reservations(self, request, queryset):
        updated = queryset.update(status='rejected')
        self.message_user(request, f'{updated} rejected.')
