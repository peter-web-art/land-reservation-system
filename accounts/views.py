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
from django.utils import timezone
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
from decimal import Decimal
from .models import User, PersonalDetails, SystemSettings, OperatorPaymentConfig

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


def stash_registration_form_state(request, form):
    values = {}
    for field in ('role', 'username', 'email', 'phone', 'first_name', 'last_name'):
        values[field] = form.data.get(field, '')

    errors = {'non_field_errors': []}
    for field, field_errors in form.errors.items():
        error_list = [str(error) for error in field_errors]
        if field == '__all__':
            errors['non_field_errors'] = error_list
        else:
            errors[field] = error_list

    request.session['register_form_state'] = {
        'values': values,
        'errors': errors,
    }


def safe_redirect_back(request, fallback):
    referer = request.POST.get('next') or request.GET.get('next') or request.META.get('HTTP_REFERER')
    if referer and url_has_allowed_host_and_scheme(
        referer,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(referer)
    return redirect(fallback)


def get_platform_fee_percentage():
    settings_obj = SystemSettings.objects.first()
    if not settings_obj:
        settings_obj = SystemSettings.objects.create()
    return settings_obj.platform_fee_percentage or Decimal('0')


def apply_platform_fee_to_payment(payment):
    fee_rate = get_platform_fee_percentage()
    payment.platform_fee_rate = fee_rate
    payment.platform_fee_amount = round((payment.amount or Decimal('0')) * fee_rate / Decimal('100'), 2)
    return payment


# ── Forms ──────────────────────────────────────────────────────────────────────

class UserRegistrationForm(forms.ModelForm):
    email           = forms.EmailField(required=True)
    phone           = forms.CharField(max_length=20, required=False)
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

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email:
            raise forms.ValidationError('Enter a valid email address.')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email address already exists.')
        return email

    def clean_first_name(self): return sanitize(self.cleaned_data.get('first_name'), 30)
    def clean_last_name(self):  return sanitize(self.cleaned_data.get('last_name'), 150)
    def clean_bio(self):        return sanitize(self.cleaned_data.get('bio'))

    def clean_phone(self):
        phone = sanitize(self.cleaned_data.get('phone', ''), 20)
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
        if cleaned.get('role') == User.ROLE_CUSTOMER and not cleaned.get('phone'):
            raise forms.ValidationError({'phone': 'Phone number is required for customer signup.'})
        
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if self.cleaned_data.get('role') == User.ROLE_OWNER:
            user.is_owner = True
        if commit:
            user.save()
        return user

    def save_personal_details(self, user):
        phone = self.cleaned_data.get('phone', '')
        if not phone:
            return

        details, created = PersonalDetails.objects.get_or_create(
            user=user,
            defaults={
                'fname': user.first_name or user.username,
                'surname': user.last_name or user.username,
                'email': user.email,
                'created_by': user,
                'updated_by': user,
            },
        )
        details.phone = phone
        details.email = user.email
        if not details.fname:
            details.fname = user.first_name or user.username
        if not details.surname:
            details.surname = user.last_name or user.username
        details.updated_by = user
        details.save()


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
    profile_picture = forms.ImageField(required=False)
    phone = forms.CharField(max_length=20, required=False)
    bio = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}), required=False)

    class Meta:
        model  = User
        fields = ('first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and getattr(self.instance, 'pk', None):
            details = getattr(self.instance, 'personal_details', None)
            if details:
                self.fields['phone'].initial = details.phone
                self.fields['bio'].initial = details.bio
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'w-full px-4 py-3 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#1a5c38]/30 focus:border-[#1a5c38] transition-colors'})

    def clean_first_name(self): return sanitize(self.cleaned_data.get('first_name'), 30)
    def clean_last_name(self):  return sanitize(self.cleaned_data.get('last_name'), 150)

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

    def clean_bio(self):
        return sanitize(self.cleaned_data.get('bio'))

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
        details, _ = PersonalDetails.objects.get_or_create(
            user=user,
            defaults={
                'fname': user.first_name or user.username,
                'surname': user.last_name or user.username,
                'email': user.email,
                'created_by': user,
                'updated_by': user,
            },
        )
        details.phone = self.cleaned_data.get('phone', '')
        details.bio = self.cleaned_data.get('bio', '')
        details.email = user.email
        if not details.fname:
            details.fname = user.first_name or user.username
        if not details.surname:
            details.surname = user.last_name or user.username
        profile_picture = self.cleaned_data.get('profile_picture')
        if profile_picture:
            details.photo_path = profile_picture
        details.updated_by = user
        if commit:
            details.save()
        return user



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
        # Store form data in session for verification step
        request.session['registration_data'] = form.cleaned_data
        return redirect('accounts:register_verify')

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        errors = {f: e.as_text() for f, e in form.errors.items()}
        from django.http import JsonResponse
        return JsonResponse({'success': False, 'errors': errors}, status=400)

    stash_registration_form_state(request, form)
    messages.error(request, 'Please correct the highlighted signup fields.')
    return auth_modal_redirect(request, 'register')
            

def register_verify(request):
    from django.conf import settings
    import requests
    
    if 'registration_data' not in request.session:
        messages.error(request, 'Registration session expired. Please try again.')
        return redirect('accounts:register')

    if request.method == 'POST':
        recaptcha_response = request.POST.get('g-recaptcha-response')
        if not recaptcha_response:
            messages.error(request, 'Please complete the reCAPTCHA.')
            return render(request, 'accounts/register_verify.html', {'recaptcha_site_key': settings.RECAPTCHA_PUBLIC_KEY})
        
        verification_data = {
            'secret': settings.RECAPTCHA_PRIVATE_KEY,
            'response': recaptcha_response,
            'remoteip': request.META.get('REMOTE_ADDR', ''),
        }
        try:
            response = requests.post(
                'https://www.google.com/recaptcha/api/siteverify',
                data=verification_data,
                timeout=10,
            )
            response.raise_for_status()
            result = response.json()
        except requests.RequestException:
            messages.error(request, 'Could not verify reCAPTCHA right now. Please try again.')
            return render(request, 'accounts/register_verify.html', {'recaptcha_site_key': settings.RECAPTCHA_PUBLIC_KEY})
        
        if result.get('success'):
            registration_data = request.session['registration_data']
            form = UserRegistrationForm(registration_data)
            if form.is_valid():
                user = form.save(commit=False)
                user.save()
                form.save_personal_details(user)
                user.created_by = user
                user.save(update_fields=['created_by'])
                del request.session['registration_data']
                messages.success(request, 'Account created successfully! Please log in to continue.')
                return auth_modal_redirect(request, 'login')
            messages.error(request, 'Invalid registration data. Please register again.')
            return redirect('accounts:register')

        messages.error(request, 'reCAPTCHA verification failed. Please try again.')
        return render(request, 'accounts/register_verify.html', {'recaptcha_site_key': settings.RECAPTCHA_PUBLIC_KEY})
    
    return render(request, 'accounts/register_verify.html', {'recaptcha_site_key': settings.RECAPTCHA_PUBLIC_KEY})
@ratelimit(key='user', rate='20/m', method='POST', block=True)
def profile_edit(request):
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            user.updated_by = request.user
            user.save()
            form.save(commit=True)
            messages.success(request, 'Profile updated successfully.')
            return redirect('accounts:profile_edit')
    else:
        form = ProfileEditForm(instance=request.user)
    from datetime import date
    return render(request, 'accounts/profile_edit.html', {'form': form, 'today_date': date.today().strftime('%Y-%m-%d')})


# ── Admin Portal ──────────────────────────────────────────────────────────────


@admin_required
def admin_portal(request):
    from lands.models import Land, Reservation, PaymentRecord
    

    # Basic stats
    total_users    = User.objects.count()
    total_admins   = User.objects.filter(role=User.ROLE_ADMIN).count()
    total_owners   = User.objects.filter(role=User.ROLE_OWNER).count()
    total_customers = User.objects.filter(role=User.ROLE_CUSTOMER).count()
    unverified     = User.objects.filter(role=User.ROLE_OWNER, is_verified=False).count()
    suspended      = User.objects.filter(is_suspended=True).count()
    total_lands    = Land.objects.count()
    total_bookings = Reservation.objects.count()
    pending_book   = Reservation.objects.filter(status='pending').count()
    awaiting_payment_book = Reservation.objects.filter(status='awaiting_payment').count()
    approved_book  = Reservation.objects.filter(status='approved').count()

    system_settings = SystemSettings.objects.first()
    if not system_settings:
        system_settings = SystemSettings.objects.create()
    platform_fee_percentage = system_settings.platform_fee_percentage or 0

    confirmed_payments = PaymentRecord.objects.filter(status='confirmed')
    gross_revenue = confirmed_payments.aggregate(total=Sum('amount'))['total'] or 0
    monthly_gross_revenue = confirmed_payments.filter(
        confirmed_on__gte=timezone.now() - timedelta(days=30)
    ).aggregate(total=Sum('amount'))['total'] or 0
    total_revenue = confirmed_payments.aggregate(total=Sum('platform_fee_amount'))['total'] or 0
    monthly_revenue = confirmed_payments.filter(
        confirmed_on__gte=timezone.now() - timedelta(days=30)
    ).aggregate(total=Sum('platform_fee_amount'))['total'] or 0
    owner_payout_total = gross_revenue - total_revenue
    monthly_owner_payout = monthly_gross_revenue - monthly_revenue

    # Recent data
    # Global Search Logic
    q = request.GET.get('q', '').strip()
    
    # Recent data with filtering
    flagged = User.objects.filter(is_suspended=True)[:10]
    recent_users = User.objects.order_by('-date_joined')
    dashboard_users = User.objects.annotate(
        total_reservations=Count('reservations', distinct=True),
        total_posts=Count('lands', distinct=True),
        total_messages=Count('sent_messages', distinct=True),
    ).order_by('-date_joined')
    
    recent_lands = Land.objects.select_related('owner').order_by('-created_on')
    recent_bookings = Reservation.objects.select_related('land', 'customer').order_by('-created_on')

    if q:
        dashboard_users = dashboard_users.filter(
            Q(username__icontains=q) | Q(email__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q)
        )
        recent_lands = recent_lands.filter(
            Q(title__icontains=q) | Q(location__icontains=q) | Q(owner__username__icontains=q)
        )
        recent_bookings = recent_bookings.filter(
            Q(customer_name__icontains=q) | Q(customer__username__icontains=q) | 
            Q(land__title__icontains=q) | Q(id__icontains=q)
        )

    earnings_by_owner_qs = confirmed_payments.select_related('reservation__land__owner')
    earnings_by_property_qs = confirmed_payments.select_related('reservation__land__owner')
    if q:
        earnings_by_owner_qs = earnings_by_owner_qs.filter(
            Q(reservation__land__owner__username__icontains=q) |
            Q(reservation__land__owner__first_name__icontains=q) |
            Q(reservation__land__owner__last_name__icontains=q) |
            Q(reservation__land__title__icontains=q)
        )
        earnings_by_property_qs = earnings_by_property_qs.filter(
            Q(reservation__land__title__icontains=q) |
            Q(reservation__land__owner__username__icontains=q)
        )

    # Apply limits after filtering
    recent_users = recent_users[:20]
    dashboard_users = dashboard_users[:100]
    recent_lands = recent_lands[:30]
    recent_bookings = recent_bookings[:30]
    recent_owners = User.objects.filter(role=User.ROLE_OWNER).order_by('-date_joined')[:20]

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

    # Platform earnings by month (last 6 months)
    revenue_trend_raw = PaymentRecord.objects.filter(
        status='confirmed'
    ).annotate(
        month=TruncMonth('confirmed_on')
    ).values('month').annotate(
        revenue=Sum('platform_fee_amount')
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

    earnings_by_owner_raw = (earnings_by_owner_qs
        .values(
            'reservation__land__owner_id',
            'reservation__land__owner__username',
            'reservation__land__owner__first_name',
            'reservation__land__owner__last_name',
        )
        .annotate(
            gross=Sum('amount'),
            platform_earnings=Sum('platform_fee_amount'),
        )
        .order_by('-platform_earnings')[:10]
    )
    earnings_by_owner = []
    for item in earnings_by_owner_raw:
        gross = item['gross'] or 0
        platform_earnings = item['platform_earnings'] or 0
        full_name = f"{item['reservation__land__owner__first_name']} {item['reservation__land__owner__last_name']}".strip()
        earnings_by_owner.append({
            'owner_id': item['reservation__land__owner_id'],
            'owner_name': full_name or item['reservation__land__owner__username'],
            'username': item['reservation__land__owner__username'],
            'gross': gross,
            'platform_earnings': platform_earnings,
            'owner_net': gross - platform_earnings,
        })

    earnings_by_property_raw = (earnings_by_property_qs
        .values(
            'reservation__land_id',
            'reservation__land__title',
            'reservation__land__owner__username',
        )
        .annotate(
            gross=Sum('amount'),
            platform_earnings=Sum('platform_fee_amount'),
        )
        .order_by('-platform_earnings')[:10]
    )
    earnings_by_property = []
    for item in earnings_by_property_raw:
        gross = item['gross'] or 0
        platform_earnings = item['platform_earnings'] or 0
        earnings_by_property.append({
            'land_id': item['reservation__land_id'],
            'title': item['reservation__land__title'],
            'owner_username': item['reservation__land__owner__username'],
            'gross': gross,
            'platform_earnings': platform_earnings,
            'owner_net': gross - platform_earnings,
        })

    # System health
    system_health = {
        'total_disk_space': 'N/A',  # Would need system monitoring
        'database_size': 'N/A',
        'active_sessions': User.objects.filter(last_login__gte=timezone.now() - timedelta(hours=1)).count(),
        'error_rate': 0,  # Would need logging system
    }

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

    # Operator payment configs to show quick access in portal
    operator_payment_configs = OperatorPaymentConfig.objects.filter(is_active=True).order_by('priority')

    return render(request, 'accounts/admin_portal.html', {
        'total_users': total_users, 'total_admins': total_admins, 'total_owners': total_owners,
        'total_customers': total_customers,
        'unverified': unverified, 'suspended': suspended,
        'total_lands': total_lands, 'total_bookings': total_bookings,
        'pending_book': pending_book, 'awaiting_payment_book': awaiting_payment_book, 'approved_book': approved_book,
        'total_revenue': total_revenue, 'monthly_revenue': monthly_revenue,
        'gross_revenue': gross_revenue, 'monthly_gross_revenue': monthly_gross_revenue,
        'owner_payout_total': owner_payout_total, 'monthly_owner_payout': monthly_owner_payout,
        'platform_fee_percentage': platform_fee_percentage,
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
        'earnings_by_owner': earnings_by_owner,
        'earnings_by_property': earnings_by_property,
        'system_health': system_health,
        'system_settings': system_settings,
        'audit_logs': audit_logs,
        'registration_form': registration_form,
        'operator_payment_configs': operator_payment_configs,
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

    return safe_redirect_back(request, 'accounts:admin_portal')


@admin_required
@require_http_methods(['POST'])
def admin_booking_action(request, booking_id):
    from lands.models import Reservation
    booking = get_object_or_404(Reservation, pk=booking_id)
    action = request.POST.get('action')

    if action == 'approve':
        booking.status = 'awaiting_payment'
        booking.updated_by = request.user
        booking.save()
        messages.success(request, f'Booking #{booking.id} moved to awaiting payment.')
    elif action == 'reject':
        booking.status = 'rejected'
        booking.updated_by = request.user
        booking.save()
        messages.success(request, f'Booking #{booking.id} rejected.')

    return safe_redirect_back(request, 'accounts:admin_portal')


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

    elif action == 'save_platform_fee':
        fee_value = request.POST.get('platform_fee_percentage', '').strip()
        try:
            fee_decimal = Decimal(fee_value)
        except Exception:
            messages.error(request, 'Enter a valid platform fee percentage.')
            return safe_redirect_back(request, 'accounts:admin_portal')

        if fee_decimal < 0 or fee_decimal > 100:
            messages.error(request, 'Platform fee percentage must be between 0 and 100.')
            return safe_redirect_back(request, 'accounts:admin_portal')

        settings.platform_fee_percentage = fee_decimal
        settings.save()
        messages.success(request, f'Platform fee updated to {fee_decimal}%.')

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
        settings.last_backup = timezone.now()
        settings.save()
        messages.success(request, "Database backup initiated successfully. (Mock)")

    return safe_redirect_back(request, 'accounts:admin_portal')


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
