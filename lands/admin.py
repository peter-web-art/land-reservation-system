from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Land, Reservation, Utility, LandImage, PaymentRecord, LandReport

class LandImageInline(admin.TabularInline):
    model = LandImage
    extra = 3

@admin.register(Land)
class LandAdmin(admin.ModelAdmin):
    list_display  = ('title', 'owner_display', 'location', 'usage',
                     'price_display', 'land_use', 'availability', 'is_active', 'is_draft', 'reservation_count')
    list_filter   = ('usage', 'land_use', 'is_active', 'is_draft')
    search_fields = ('title', 'location', 'owner__username', 'owner__email')
    ordering      = ('-created_on',)
    readonly_fields = ('reservation_count',)
    list_editable  = ('is_active',)
    inlines = [LandImageInline]
    actions = ['delete_selected']  # Enable bulk delete from admin
    fieldsets = (
        ('Basic',   {'fields': ('title', 'description', 'owner', 'is_active', 'is_draft')}),
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


@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    """Admin interface for managing payment records and confirmations."""
    list_display = ('payment_reference', 'reservation_display', 'customer_display', 
                   'amount_display', 'status_badge', 'payment_method', 'created_on', 'admin_action_buttons')
    list_filter = ('status', 'payment_method', 'created_on', 'confirmed_on')
    search_fields = ('payment_reference', 'reservation__customer__username', 
                    'reservation__customer_email', 'reservation__land__title')
    readonly_fields = ('created_by', 'created_on', 'updated_by', 'updated_on', 
                      'confirmed_on', 'platform_fee_amount', 'owner_net_amount')
    date_hierarchy = 'created_on'
    ordering = ('-created_on',)
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('reservation', 'payment_reference', 'amount', 'payment_method', 'payment_date', 'status')
        }),
        ('Payment Proof', {
            'fields': ('payment_receipt', 'notes')
        }),
        ('Platform Fee & Calculations', {
            'fields': ('platform_fee_rate', 'platform_fee_amount', 'owner_net_amount')
        }),
        ('Admin Confirmation', {
            'fields': ('confirmed_on', 'owner_received_on')
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_on', 'updated_by', 'updated_on'),
            'classes': ('collapse',)
        }),
    )
    
    def reservation_display(self, obj):
        """Display reservation with land title and booking ID."""
        return format_html(
            '<a href="/admin/lands/reservation/{}/change/">{} - {}</a>',
            obj.reservation.id,
            obj.reservation.id,
            obj.reservation.land.title
        )
    reservation_display.short_description = 'Booking'
    
    def customer_display(self, obj):
        """Display customer name and email."""
        customer_name = obj.reservation.customer.username if obj.reservation.customer else obj.reservation.customer_name
        return format_html(
            '<div><strong>{}</strong><br/><small style="color: #666;">{}</small></div>',
            customer_name,
            obj.reservation.customer_email
        )
    customer_display.short_description = 'Customer'
    
    def amount_display(self, obj):
        """Display payment amount with fee calculation."""
        fee = obj.platform_fee_amount or 0
        net = obj.owner_net_amount or 0
        return format_html(
            '<div><strong>Tsh {:,.0f}</strong><br/>'
            '<small style="color: #666;">Fee: Tsh {:,.0f} → Owner: Tsh {:,.0f}</small></div>',
            obj.amount or 0,
            fee,
            net
        )
    amount_display.short_description = 'Amount (Fee → Net)'
    
    def status_badge(self, obj):
        """Display status as colored badge."""
        colors = {
            'submitted': '#f59e0b',  # Amber
            'confirmed': '#10b981',  # Green
            'rejected': '#ef4444',   # Red
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{};color:white;padding:3px 10px;border-radius:4px;font-weight:600;font-size:11px;">{}</span>',
            color,
            obj.get_status_display().upper()
        )
    status_badge.short_description = 'Status'
    
    def admin_action_buttons(self, obj):
        """Display action buttons for admin to confirm/reject."""
        if obj.status == 'submitted':
            return format_html(
                '<a class="button" href="/accounts/admin-portal/payments/{}/confirm/" style="background:#10b981;">Confirm</a> '
                '<a class="button" href="/accounts/admin-portal/payments/{}/reject/" style="background:#ef4444;">Reject</a>',
                obj.id, obj.id
            )
        else:
            return '—'
    admin_action_buttons.short_description = 'Actions'


@admin.register(LandReport)
class LandReportAdmin(admin.ModelAdmin):
    """Admin interface for managing user reports on lands."""
    list_display = ('id', 'land', 'reported_by', 'reason', 'status', 'created_on', 'reviewed_by')
    list_filter = ('status', 'reason', 'is_spam', 'created_on')
    search_fields = ('land__title', 'reported_by__username', 'reported_by__email', 'admin_notes')
    readonly_fields = ('created_on', 'reviewed_on')
    ordering = ('-created_on',)

    actions = ['mark_reviewed', 'mark_resolved', 'mark_spam']

    def mark_reviewed(self, request, queryset):
        queryset.update(status='reviewed', reviewed_by=request.user, reviewed_on=timezone.now())
        self.message_user(request, f"Marked {queryset.count()} report(s) as reviewed.")
    mark_reviewed.short_description = 'Mark selected reports as Reviewed'

    def mark_resolved(self, request, queryset):
        queryset.update(status='resolved', reviewed_by=request.user, reviewed_on=timezone.now())
        self.message_user(request, f"Marked {queryset.count()} report(s) as Resolved.")
    mark_resolved.short_description = 'Mark selected reports as Resolved'

    def mark_spam(self, request, queryset):
        queryset.update(is_spam=True, status='resolved', reviewed_by=request.user, reviewed_on=timezone.now())
        self.message_user(request, f"Marked {queryset.count()} report(s) as Spam and resolved.")
    mark_spam.short_description = 'Mark selected reports as Spam'

