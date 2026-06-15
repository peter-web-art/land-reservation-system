from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from .models import User, PersonalDetails, PaymentDetails, OperatorPaymentConfig


class PersonalDetailsInline(admin.StackedInline):
    model = PersonalDetails
    can_delete = False
    verbose_name_plural = 'Personal Details'
    fk_name = 'user'


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'username', 'get_full_name_display', 'email', 'role_badge',
        'verified_badge', 'suspended_badge', 'date_joined', 'actions_col'
    )
    list_filter   = ('role', 'is_verified', 'is_suspended', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering      = ('-date_joined',)
    actions       = ['verify_owners', 'unverify_owners', 'suspend_users', 'unsuspend_users']
    inlines       = [PersonalDetailsInline]

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Role & Status', {'fields': ('role', 'is_owner', 'is_verified', 'is_suspended')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'role', 'password1', 'password2'),
        }),
    )

    def get_full_name_display(self, obj):
        return obj.get_full_name() or '—'
    get_full_name_display.short_description = 'Full Name'

    def role_badge(self, obj):
        colors = {'customer': '#1a5276', 'owner': '#1e5229', 'admin': '#7b241c'}
        color  = colors.get(obj.role, '#555')
        return format_html(
            '<span style="background:{};color:white;padding:2px 10px;border-radius:999px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_role_display()
        )
    role_badge.short_description = 'Role'

    def verified_badge(self, obj):
        if obj.is_verified:
            return format_html('<span style="color:#1e5229;font-weight:700;">✔ Verified</span>')
        return format_html('<span style="color:#999;">— Unverified</span>')
    verified_badge.short_description = 'Verified'

    def suspended_badge(self, obj):
        if obj.is_suspended:
            return format_html('<span style="color:#c0392b;font-weight:700;">⛔ Suspended</span>')
        return format_html('<span style="color:#1e5229;">✔ Active</span>')
    suspended_badge.short_description = 'Status'

    def actions_col(self, obj):
        url = reverse('admin:accounts_user_change', args=[obj.pk])
        return format_html('<a href="{}" style="font-size:12px;">Edit →</a>', url)
    actions_col.short_description = ''

    @admin.action(description='✔ Verify selected owners')
    def verify_owners(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'{updated} user(s) verified.')

    @admin.action(description='✘ Remove verification')
    def unverify_owners(self, request, queryset):
        updated = queryset.update(is_verified=False)
        self.message_user(request, f'{updated} user(s) unverified.')

    @admin.action(description='⛔ Suspend selected users')
    def suspend_users(self, request, queryset):
        updated = queryset.update(is_suspended=True, is_active=False)
        self.message_user(request, f'{updated} user(s) suspended.')

    @admin.action(description='✔ Unsuspend selected users')
    def unsuspend_users(self, request, queryset):
        updated = queryset.update(is_suspended=False, is_active=True)
        self.message_user(request, f'{updated} user(s) unsuspended.')


# ═══════════════════════════════════════════════════════════════════════════════
# PAYMENT DETAILS ADMIN
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(PaymentDetails)
class PaymentDetailsAdmin(admin.ModelAdmin):
    list_display = ('user_display', 'payment_method_badge', 'account_identifier', 'is_verified_badge', 'is_default', 'updated_on')
    list_filter = ('payment_method', 'is_verified', 'is_default', 'updated_on')
    search_fields = ('user__username', 'account_identifier', 'account_holder_name')
    readonly_fields = ('created_on', 'updated_on', 'created_by', 'updated_by', 'verified_on')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Payment Details', {
            'fields': ('payment_method', 'account_identifier', 'account_holder_name', 'bank_name', 'bank_branch')
        }),
        ('Status', {
            'fields': ('is_verified', 'verified_on', 'is_default')
        }),
        ('Audit', {
            'fields': ('created_by', 'created_on', 'updated_by', 'updated_on'),
            'classes': ('collapse',)
        }),
    )

    def user_display(self, obj):
        return format_html('{} <span style="color:#999;">({})</span>', obj.user.username, obj.user.get_role_display())
    user_display.short_description = 'User'

    def payment_method_badge(self, obj):
        colors = {'mpesa': '#22863a', 'airtel': '#cb2431', 'tigo': '#6f42c1', 'bank_transfer': '#005a9c', 'bank_cheque': '#555'}
        color = colors.get(obj.payment_method, '#999')
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:3px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_payment_method_display()
        )
    payment_method_badge.short_description = 'Payment Method'

    def is_verified_badge(self, obj):
        if obj.is_verified:
            return format_html('<span style="color:#22863a;font-weight:700;">✔ Verified</span>')
        return format_html('<span style="color:#cb2431;font-weight:700;">✘ Not Verified</span>')
    is_verified_badge.short_description = 'Verified'


# ═══════════════════════════════════════════════════════════════════════════════
# OPERATOR PAYMENT CONFIG ADMIN
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(OperatorPaymentConfig)
class OperatorPaymentConfigAdmin(admin.ModelAdmin):
    list_display = ('payment_method_badge', 'account_identifier', 'is_active_badge', 'priority', 'is_active', 'updated_on', 'actions_col')
    list_filter = ('payment_method', 'is_active', 'created_on')
    search_fields = ('account_identifier', 'account_holder_name', 'bank_name')
    readonly_fields = ('created_on', 'updated_on', 'created_by', 'updated_by')
    list_editable = ('priority', 'is_active')
    
    fieldsets = (
        ('Payment Method Configuration', {
            'fields': ('payment_method', 'account_identifier', 'account_holder_name')
        }),
        ('Bank Details (if applicable)', {
            'fields': ('bank_name', 'bank_branch'),
            'classes': ('collapse',),
        }),
        ('Instructions & Status', {
            'fields': ('instructions', 'is_active', 'priority')
        }),
        ('Audit', {
            'fields': ('created_by', 'created_on', 'updated_by', 'updated_on'),
            'classes': ('collapse',)
        }),
    )

    def payment_method_badge(self, obj):
        colors = {'mpesa': '#22863a', 'airtel': '#cb2431', 'tigo': '#6f42c1', 'bank_transfer': '#005a9c', 'bank_cheque': '#555'}
        color = colors.get(obj.payment_method, '#999')
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:3px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_payment_method_display()
        )
    payment_method_badge.short_description = 'Payment Method'

    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color:#22863a;font-weight:700;">✔ Active</span>')
        return format_html('<span style="color:#cb2431;font-weight:700;">✘ Inactive</span>')
    is_active_badge.short_description = 'Status'

    def actions_col(self, obj):
        url = reverse('admin:accounts_operatorpaymentconfig_change', args=[obj.pk])
        return format_html('<a href="{}" style="font-size:12px;">Edit →</a>', url)
    actions_col.short_description = ''

    @admin.action(description='✘ Remove verification')
    def unverify_owners(self, request, queryset):
        updated = queryset.update(is_verified=False)
        self.message_user(request, f'{updated} user(s) unverified.')

    @admin.action(description='⛔ Suspend selected users')
    def suspend_users(self, request, queryset):
        updated = queryset.update(is_suspended=True, is_active=False)
        self.message_user(request, f'{updated} user(s) suspended.')

    @admin.action(description='✔ Unsuspend selected users')
    def unsuspend_users(self, request, queryset):
        updated = queryset.update(is_suspended=False, is_active=True)
        self.message_user(request, f'{updated} user(s) unsuspended.')
