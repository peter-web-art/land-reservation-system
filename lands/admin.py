from django.contrib import admin
from django.utils.html import format_html
from .models import Land, Reservation, Utility

@admin.register(Land)
class LandAdmin(admin.ModelAdmin):
    list_display  = ('title', 'owner_display', 'location', 'usage',
                     'price_display', 'land_use', 'availability', 'is_active', 'reservation_count')
    list_filter   = ('usage', 'land_use', 'is_active')
    search_fields = ('title', 'location', 'owner__username', 'owner__email')
    ordering      = ('-created_on',)
    readonly_fields = ('reservation_count',)
    list_editable  = ('is_active',)
    inlines = []
    actions = ['delete_selected']  # Enable bulk delete from admin
    fieldsets = (
        ('Basic',   {'fields': ('title', 'description', 'owner', 'is_active')}),
        ('Location & Details', {'fields': ('location', 'latitude', 'longitude', 'usage', 'land_use', 'size', 'size_unit', 'topography', 'utilities')}),
        ('Pricing', {'fields': ('price', 'price_unit', 'weekly_discount', 'monthly_discount',
                                'min_duration_days', 'max_duration_days')}),
        ('Contact', {'fields': ('contact_phone', 'contact_email', 'land_image_path')}),
    )

    def owner_display(self, obj):
        v = ' ✔' if obj.owner.is_verified else ''
        return format_html('{}{}', obj.owner.username, v)
    owner_display.short_description = 'Owner'

    def price_display(self, obj):
        return obj.price_display
    price_display.short_description = 'Price'

    def availability(self, obj):
        return obj.status_display
    availability.short_description = 'Status'

    def reservation_count(self, obj):
        return obj.reservations.count()
    reservation_count.short_description = 'Bookings'

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('land', 'customer', 'start_date', 'end_date', 'status', 'payment_status', 'total_amount')
    list_filter = ('status', 'payment_status', 'created_on')
    search_fields = ('land__title', 'customer__username', 'customer__email')
    date_hierarchy = 'created_on'

@admin.register(Utility)
class UtilityAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon_class')
    search_fields = ('name',)
