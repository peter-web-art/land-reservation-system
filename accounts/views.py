from urllib.parse import urlencode

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Avg, Q
from django.db.models.functions import TruncMonth
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
import re
from django import forms
from django.utils.html import strip_tags
import bleach
import random
import string
import csv
import json
from datetime import datetime, timedelta
from .models import User, PersonalDetails, SystemSettings

try:
    from django_ratelimit.decorators import ratelimit
except ImportError:
    def ratelimit(*args, **kwargs):
        def decorator(func): return func
        return decorator

from .decorators import admin_required


def sanitize(value, max_length=None):
    if not value:
        return value
    cleaned = bleach.clean(value, tags=[], strip=True)
    cleaned = strip_tags(cleaned).strip()
    if max_length:
        cleaned = cleaned[:max_length]
    return cleaned


def auth_modal_redirect(request, tab='login'):
    params = {'auth': tab}
    next_url = request.POST.get('next') or request.GET.get('next') or ''
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        params['next'] = next_url
    return redirect(f"{reverse('lands:land_list')}?{urlencode(params)}")


# ── Forms ──────────────────────────────────────────────────────────────────────

class UserRegistrationForm(forms.ModelForm):
    email           = forms.EmailField(required=True)
    first_name      = forms.CharField(max_length=30, required=False)
    last_name       = forms.CharField(max_length=150, required=False)
    password1       = forms.CharField(widget=forms.PasswordInput(), label='Password')
    password2       = forms.CharField(widget=forms.PasswordInput(), label='Confirm Password')
    role            = forms.ChoiceField(
        choices=[(User.ROLE_CUSTOMER, 'Customer'), (User.ROLE_OWNER, 'Land Owner')],
        initial=User.ROLE_CUSTOMER
    )

    class Meta:
        model  = User
        fields = ('username', 'email', 'first_name', 'last_name', 'role')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'w-full px-4 py-3 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#1a5c38]/30 focus:border-[#1a5c38] transition-colors'})

    def clean_username(self):
        val = self.cleaned_data.get('username', '')
        if not re.match(r'^[\w.@+-]{3,150}$', val):
            raise forms.ValidationError(
                'Username may only contain letters, numbers, and @/./+/-/_ (min 3 chars).')
        return val

    def clean_first_name(self): return sanitize(self.cleaned_data.get('first_name'), 30)
    def clean_last_name(self):  return sanitize(self.cleaned_data.get('last_name'), 150)
    def clean_bio(self):        return sanitize(self.cleaned_data.get('bio'))

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if phone and not re.match(r'^[\d\+\s\-\(\)]{6,20}$', phone):
            raise forms.ValidationError('Enter a valid phone number.')
        return phone

    def clean_profile_picture(self):
        image = self.cleaned_data.get('profile_picture')
        if image and hasattr(image, 'content_type'):
            if image.content_type not in ['image/jpeg', 'image/png', 'image/webp']:
                raise forms.ValidationError('Use JPG, PNG, or WebP.')
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Image must be under 5 MB.')
        return image

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get('password1'), cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError({'password2': 'Passwords do not match.'})
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if self.cleaned_data.get('role') == User.ROLE_OWNER:
            user.is_owner = True
        if commit:
            user.save()
        return user


class AdminUserRegistrationForm(UserRegistrationForm):
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        initial=User.ROLE_CUSTOMER
    )

    class Meta(UserRegistrationForm.Meta):
        fields = ('username', 'email', 'first_name', 'last_name', 'role')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if self.cleaned_data.get('role') == User.ROLE_OWNER:
            user.is_owner = True
        elif self.cleaned_data.get('role') == User.ROLE_ADMIN:
            user.is_staff = True
            user.is_superuser = False # Keep it as regular admin unless manually changed
        if commit:
            user.save()
        return user



class ProfileEditForm(forms.ModelForm):
    class Meta:
        model  = User
        fields = ('first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'w-full px-4 py-3 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#1a5c38]/30 focus:border-[#1a5c38] transition-colors'})

    def clean_first_name(self): return sanitize(self.cleaned_data.get('first_name'), 30)
    def clean_last_name(self):  return sanitize(self.cleaned_data.get('last_name'), 150)


# ── Auth Views ────────────────────────────────────────────────────────────────

@ratelimit(key='ip', rate='10/m', method='POST', block=True)
def login_view(request):
    if request.method != 'POST':
        return auth_modal_redirect(request, 'login')

    username = sanitize(request.POST.get('username', ''), 150)
    password = request.POST.get('password', '')

    user = authenticate(request, username=username, password=password)

    if user is None:
        messages.error(request, 'Invalid username or password. Please try again.')
        return auth_modal_redirect(request, 'login')

    auth_login(request, user, backend='accounts.backends.SuspendedAwareBackend')
    messages.success(request, f'Welcome back, {user.username}.')

    # Auto-redirect based on user's stored role — no role selection needed
    from .decorators import role_based_redirect
    return redirect(role_based_redirect(user))


@ratelimit(key='ip', rate='10/m', method='POST', block=True)
def register(request):
    if request.method != 'POST':
        return auth_modal_redirect(request, 'register')

    form = UserRegistrationForm(request.POST, request.FILES)
    if form.is_valid():
        user = form.save(commit=False)
        user.created_by = user  # Self-created
        user.save()
        messages.success(request, f'Account created successfully! Please log in to continue.')
        # Redirect to login — do NOT auto-login after registration
        return auth_modal_redirect(request, 'login')

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        errors = {f: e.as_text() for f, e in form.errors.items()}
        from django.http import JsonResponse
        return JsonResponse({'success': False, 'errors': errors}, status=400)

    for field, errors in form.errors.items():
        label = form.fields.get(field).label if field in form.fields else 'Error'
        for error in errors:
            messages.error(request, f'{label}: {error}')
    return auth_modal_redirect(request, 'register')


@login_required
@ratelimit(key='user', rate='20/m', method='POST', block=True)
def profile_edit(request):
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            user.updated_by = request.user
            user.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('accounts:profile_edit')
    else:
        form = ProfileEditForm(instance=request.user)
    from datetime import date
    return render(request, 'accounts/profile_edit.html', {'form': form, 'today_date': date.today().strftime('%Y-%m-%d')})


# ── Admin Portal ──────────────────────────────────────────────────────────────


@admin_required
def admin_portal(request):
    from lands.models import Land, Reservation

    # Basic stats
    total_users    = User.objects.count()
    total_owners   = User.objects.filter(role=User.ROLE_OWNER).count()
    total_customers = User.objects.filter(role=User.ROLE_CUSTOMER).count()
    unverified     = User.objects.filter(role=User.ROLE_OWNER, is_verified=False).count()
    suspended      = User.objects.filter(is_suspended=True).count()
    total_lands    = Land.objects.count()
    total_bookings = Reservation.objects.count()
    pending_book   = Reservation.objects.filter(status='pending').count()
    approved_book  = Reservation.objects.filter(status='approved').count()

    # Revenue stats
    total_revenue = Reservation.objects.filter(payment_status='paid').aggregate(
        total=Sum('amount_paid'))['total'] or 0
    monthly_revenue = Reservation.objects.filter(
        payment_status='paid', created_on__gte=datetime.now() - timedelta(days=30)
    ).aggregate(total=Sum('amount_paid'))['total'] or 0

    # Recent data
    flagged        = User.objects.filter(is_suspended=True)[:10]
    recent_users   = User.objects.order_by('-date_joined')[:20]
    dashboard_users = User.objects.annotate(
        total_reservations=Count('reservations', distinct=True),
        total_posts=Count('lands', distinct=True),
        total_messages=Count('sent_messages', distinct=True),
    ).order_by('-date_joined')[:50]
    recent_owners  = User.objects.filter(role=User.ROLE_OWNER).order_by('-date_joined')[:20]
    recent_lands   = Land.objects.select_related('owner').order_by('-created_on')[:15]
    recent_bookings = Reservation.objects.select_related('land', 'customer').order_by('-created_on')[:15]

    # Analytics data for charts
    # User registration trend (last 12 months)
    user_trend_raw = User.objects.annotate(
        month=TruncMonth('date_joined')
    ).values('month').annotate(count=Count('id')).order_by('-month')[:12]

    # Format user trend data for Chart.js
    user_trend = []
    for item in reversed(list(user_trend_raw)):
        user_trend.append({
            'month': item['month'].strftime('%b %Y') if item['month'] else 'Unknown',
            'count': item['count']
        })

    # Booking status distribution
    booking_stats_raw = Reservation.objects.values('status').annotate(count=Count('id'))
    booking_stats = []
    status_labels = {'pending': 'Pending', 'approved': 'Approved', 'rejected': 'Rejected', 'cancelled': 'Cancelled'}
    for item in booking_stats_raw:
        booking_stats.append({
            'status': status_labels.get(item['status'], item['status'].title()),
            'count': item['count']
        })

    # Revenue by month (last 6 months)
    revenue_trend_raw = Reservation.objects.filter(
        payment_status='paid'
    ).annotate(
        month=TruncMonth('created_on')
    ).values('month').annotate(
        revenue=Sum('amount_paid')
    ).order_by('-month')[:6]

    # Format revenue trend data for Chart.js
    revenue_trend = []
    for item in reversed(list(revenue_trend_raw)):
        revenue_trend.append({
            'month': item['month'].strftime('%b %Y') if item['month'] else 'Unknown',
            'revenue': float(item['revenue'] or 0)
        })

    # Top performing lands
    top_lands = Land.objects.annotate(
        booking_count=Count('reservations')
    ).order_by('-booking_count')[:10]

    # System health
    system_health = {
        'total_disk_space': 'N/A',  # Would need system monitoring
        'database_size': 'N/A',
        'active_sessions': User.objects.filter(last_login__gte=datetime.now() - timedelta(hours=1)).count(),
        'error_rate': 0,  # Would need logging system
    }

    # System Settings
    system_settings = SystemSettings.objects.first()
    if not system_settings:
        system_settings = SystemSettings.objects.create()

    # User Registration Form for Admin
    registration_form = AdminUserRegistrationForm()

    # Aggregate Audit Logs
    audit_logs = []
    
    # Recent User creations/updates
    for u in User.objects.order_by('-updated_on')[:15]:
        audit_logs.append({
            'model': 'User',
            'icon': 'bi-person',
            'object': u.username,
            'created_on': u.created_on,
            'created_by': u.created_by.username if u.created_by else 'Self/System',
            'updated_on': u.updated_on,
            'updated_by': u.updated_by.username if u.updated_by else 'System',
            'timestamp': u.updated_on
        })

    # Recent Land creations/updates
    for l in Land.objects.select_related('created_by', 'updated_by').order_by('-updated_on')[:15]:
        audit_logs.append({
            'model': 'Land',
            'icon': 'bi-geo-alt',
            'object': l.title,
            'created_on': l.created_on,
            'created_by': l.created_by.username if l.created_by else 'Owner',
            'updated_on': l.updated_on,
            'updated_by': l.updated_by.username if l.updated_by else 'System',
            'timestamp': l.updated_on
        })

    # Recent Reservation creations/updates
    for r in Reservation.objects.select_related('created_by', 'updated_by', 'land').order_by('-updated_on')[:15]:
        audit_logs.append({
            'model': 'Reservation',
            'icon': 'bi-calendar-check',
            'object': f"Booking for {r.land.title}",
            'created_on': r.created_on,
            'created_by': r.created_by.username if r.created_by else 'System',
            'updated_on': r.updated_on,
            'updated_by': r.updated_by.username if r.updated_by else 'System',
            'timestamp': r.updated_on
        })

    audit_logs.sort(key=lambda x: x['timestamp'], reverse=True)
    audit_logs = audit_logs[:40]

    return render(request, 'accounts/admin_portal.html', {
        'total_users': total_users, 'total_owners': total_owners,
        'total_customers': total_customers,
        'unverified': unverified, 'suspended': suspended,
        'total_lands': total_lands, 'total_bookings': total_bookings,
        'pending_book': pending_book, 'approved_book': approved_book,
        'total_revenue': total_revenue, 'monthly_revenue': monthly_revenue,
        'recent_users': recent_users,
        'dashboard_users': dashboard_users,
        'recent_owners': recent_owners,
        'flagged': flagged,
        'recent_lands': recent_lands,
        'recent_bookings': recent_bookings,
        'user_trend': user_trend,
        'booking_stats': booking_stats,
        'revenue_trend': revenue_trend,
        'top_lands': top_lands,
        'system_health': system_health,
        'system_settings': system_settings,
        'audit_logs': audit_logs,
        'registration_form': registration_form,
    })


@admin_required
def admin_register_user(request):
    if request.method == 'POST':
        form = AdminUserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.created_by = request.user
            user.save()
            messages.success(request, f'User {user.username} has been registered successfully.')
        else:
            for field, errors in form.errors.items():
                label = form.fields.get(field).label if field in form.fields else 'Error'
                for error in errors:
                    messages.error(request, f'{label}: {error}')
    return redirect('accounts:admin_portal')


@admin_required
@require_http_methods(['POST'])
def admin_user_action(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    action = request.POST.get('action')

    if action == 'verify':
        target.is_verified = True
        target.updated_by = request.user
        target.save()
        messages.success(request, f'{target.username} verified as trusted owner.')
    elif action == 'unverify':
        target.is_verified = False
        target.updated_by = request.user
        target.save()
        messages.success(request, f'{target.username} verification removed.')
    elif action == 'suspend':
        target.is_suspended = True
        target.is_active    = False
        target.updated_by = request.user
        target.save()
        messages.warning(request, f'{target.username} has been suspended.')
    elif action == 'unsuspend':
        target.is_suspended = False
        target.is_active    = True
        target.updated_by = request.user
        target.save()
        messages.success(request, f'{target.username} has been unsuspended.')
    elif action == 'make_owner':
        target.role     = User.ROLE_OWNER
        target.is_owner = True
        target.updated_by = request.user
        target.save()
        messages.success(request, f'{target.username} promoted to Land Owner.')
    elif action == 'reset_password':
        # Generate a new random password
        new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        target.set_password(new_password)
        target.updated_by = request.user
        target.save()
        messages.success(request, f'Password reset for {target.username}. New password: {new_password} (Please share securely)')
    elif action == 'delete_user':
        if target.is_staff or target.role == User.ROLE_ADMIN:
            messages.error(request, 'Cannot delete admin users.')
        else:
            username = target.username
            target.delete()
            messages.success(request, f'{username} has been permanently deleted.')

    return redirect('accounts:admin_portal')


@admin_required
@require_http_methods(['POST'])
def admin_booking_action(request, booking_id):
    from lands.models import Reservation
    booking = get_object_or_404(Reservation, pk=booking_id)
    action = request.POST.get('action')

    if action == 'approve':
        booking.status = 'approved'
        booking.updated_by = request.user
        booking.save()
        messages.success(request, f'Booking #{booking.id} approved.')
    elif action == 'reject':
        booking.status = 'rejected'
        booking.updated_by = request.user
        booking.save()
        messages.success(request, f'Booking #{booking.id} rejected.')

    return redirect('accounts:admin_portal')


@admin_required
@require_http_methods(['POST'])
def admin_system_action(request):
    action = request.POST.get('action')
    settings = SystemSettings.objects.first()
    if not settings:
        settings = SystemSettings.objects.create()

    if action == 'toggle_maintenance':
        settings.maintenance_mode = not settings.maintenance_mode
        settings.save()
        status = "enabled" if settings.maintenance_mode else "disabled"
        messages.success(request, f"Maintenance mode {status}.")

    elif action == 'toggle_emails':
        settings.email_notifications = not settings.email_notifications
        settings.save()
        status = "enabled" if settings.email_notifications else "disabled"
        messages.success(request, f"Email notifications {status}.")

    elif action == 'export_data':
        # Export users as CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="users_export.csv"'
        writer = csv.writer(response)
        writer.writerow(['Username', 'Email', 'Role', 'Joined', 'Verified', 'Suspended'])
        users = User.objects.all()
        for u in users:
            writer.writerow([u.username, u.email, u.role, u.date_joined, u.is_verified, u.is_suspended])
        return response

    elif action == 'backup_db':
        # Mock backup for demonstration
        settings.last_backup = datetime.now()
        settings.save()
        messages.success(request, "Database backup initiated successfully. (Mock)")

    return redirect('accounts:admin_portal')


# ── Admin Login ───────────────────────────────────────────────────────────────

def admin_login(request):
    """Separate admin login that bypasses normal authentication flow."""
    if request.user.is_authenticated and (request.user.is_staff or request.user.role == User.ROLE_ADMIN):
        return redirect('accounts:admin_portal')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user and user.is_active and (user.is_staff or user.role == User.ROLE_ADMIN):
            auth_login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('accounts:admin_portal')
        else:
            messages.error(request, 'Invalid admin credentials or insufficient permissions.')

    return render(request, 'accounts/admin_login.html')


def owner_login(request):
    """Redirect to unified login — separate owner login is no longer needed."""
    if request.user.is_authenticated and (request.user.is_owner or request.user.role == User.ROLE_OWNER):
        return redirect('lands:owner_dashboard')
    return auth_modal_redirect(request, 'login')
