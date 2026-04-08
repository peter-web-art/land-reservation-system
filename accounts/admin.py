from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'username', 'get_full_name_display', 'email', 'role_badge',
        'verified_badge', 'suspended_badge', 'phone', 'date_joined', 'actions_col'
    )
    list_filter   = ('role', 'is_verified', 'is_suspended', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone')
    ordering      = ('-date_joined',)
    actions       = ['verify_owners', 'unverify_owners', 'suspend_users', 'unsuspend_users']

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email', 'phone', 'bio', 'profile_picture')}),
        ('Role & Status', {'fields': ('role', 'is_owner', 'is_verified', 'is_suspended')}),
        ('KYC Documents', {'fields': ('kyc_document', 'kyc_status', 'kyc_notes',
                                      'govt_letter', 'govt_letter_date'),
                           'classes': ('collapse',)}),
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
