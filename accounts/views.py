from urllib.parse import urlencode

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django import forms
from django.utils.html import strip_tags
from django.utils.http import url_has_allowed_host_and_scheme
from django.db.models import Count, Q, Sum
from django.urls import reverse
from django.db.models.functions import TruncMonth
from datetime import datetime, timedelta
import bleach, re, json
import string, random

try:
    from django_ratelimit.decorators import ratelimit
except ImportError:
    def ratelimit(*args, **kwargs):
        def decorator(func): return func
        return decorator

from .models import User
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
    phone           = forms.CharField(max_length=20, required=False)
    profile_picture = forms.ImageField(required=False)
    bio             = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)
    password1       = forms.CharField(widget=forms.PasswordInput(), label='Password')
    password2       = forms.CharField(widget=forms.PasswordInput(), label='Confirm Password')
    role            = forms.ChoiceField(
        choices=[(User.ROLE_CUSTOMER, 'Customer'), (User.ROLE_OWNER, 'Land Owner')],
        initial=User.ROLE_CUSTOMER
    )

    class Meta:
        model  = User
        fields = ('username', 'email', 'first_name', 'last_name',
                  'phone', 'profile_picture', 'bio', 'role')

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


class ProfileEditForm(forms.ModelForm):
    class Meta:
        model  = User
        fields = ('first_name', 'last_name', 'email', 'phone', 'bio', 'profile_picture')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'w-full px-4 py-3 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#1a5c38]/30 focus:border-[#1a5c38] transition-colors'})

    def clean_bio(self):        return sanitize(self.cleaned_data.get('bio'))
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
        user = form.save()
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
            form.save()
            messages.success(request, 'Profile updated successfully!')
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
        payment_status='paid', booking_date__gte=datetime.now() - timedelta(days=30)
    ).aggregate(total=Sum('amount_paid'))['total'] or 0

    # Recent data
    kyc_pending    = User.objects.filter(kyc_status='pending').order_by('-date_joined')
    flagged        = User.objects.filter(is_suspended=True)[:10]
    recent_users   = User.objects.order_by('-date_joined')[:20]
    dashboard_users = User.objects.annotate(
        total_reservations=Count('reservations', distinct=True),
        total_posts=Count('lands', distinct=True),
        total_messages=Count('sent_messages', distinct=True),
    ).order_by('-date_joined')[:50]
    recent_owners  = User.objects.filter(role=User.ROLE_OWNER).order_by('-date_joined')[:20]
    recent_lands   = Land.objects.select_related('owner').order_by('-created_at')[:15]
    recent_bookings = Reservation.objects.select_related('land', 'customer').order_by('-booking_date')[:15]

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
        month=TruncMonth('booking_date')
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

    return render(request, 'accounts/admin_portal.html', {
        'total_users': total_users, 'total_owners': total_owners,
        'total_customers': total_customers,
        'unverified': unverified, 'suspended': suspended,
        'total_lands': total_lands, 'total_bookings': total_bookings,
        'pending_book': pending_book, 'approved_book': approved_book,
        'total_revenue': total_revenue, 'monthly_revenue': monthly_revenue,
        'kyc_pending': kyc_pending,
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
    })


@admin_required
@require_http_methods(['POST'])
def admin_user_action(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    action = request.POST.get('action')

    if action == 'verify':
        target.is_verified = True
        target.save()
        messages.success(request, f'{target.username} verified as trusted owner.')
    elif action == 'unverify':
        target.is_verified = False
        target.save()
        messages.success(request, f'{target.username} verification removed.')
    elif action == 'suspend':
        target.is_suspended = True
        target.is_active    = False
        target.save()
        messages.warning(request, f'{target.username} has been suspended.')
    elif action == 'unsuspend':
        target.is_suspended = False
        target.is_active    = True
        target.save()
        messages.success(request, f'{target.username} has been unsuspended.')
    elif action == 'make_owner':
        target.role     = User.ROLE_OWNER
        target.is_owner = True
        target.save()
        messages.success(request, f'{target.username} promoted to Land Owner.')
    elif action == 'reset_password':
        # Generate a new random password
        new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        target.set_password(new_password)
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
        booking.save()
        messages.success(request, f'Booking #{booking.id} approved.')
    elif action == 'reject':
        booking.status = 'rejected'
        booking.save()
        messages.success(request, f'Booking #{booking.id} rejected.')

    return redirect('accounts:admin_portal')


# ── KYC Views ─────────────────────────────────────────────────────────────────

@login_required
def submit_kyc(request):
    if request.method == 'POST':
        from datetime import date, timedelta
        doc       = request.FILES.get('kyc_document')
        ownership_doc = request.FILES.get('ownership_proof')
        govt_doc  = request.FILES.get('govt_letter')
        govt_date_str = request.POST.get('govt_letter_date', '').strip()
        allowed = ['image/jpeg','image/png','image/webp','application/pdf']
        errors = []

        # Validate identity document
        if not doc and not request.user.kyc_document:
            errors.append('Please upload your ID document.')
        elif doc:
            if doc.content_type not in allowed:
                errors.append('ID document: use JPG, PNG, WebP, or PDF only.')
            elif doc.size > 10 * 1024 * 1024:
                errors.append('ID document must be under 10 MB.')

        # Validate ownership proof. This can be skipped only when the ID upload
        # already contains the ownership evidence as a combined document.
        if ownership_doc:
            if ownership_doc.content_type not in allowed:
                errors.append('Ownership proof: use JPG, PNG, WebP, or PDF only.')
            elif ownership_doc.size > 10 * 1024 * 1024:
                errors.append('Ownership proof must be under 10 MB.')
        elif not request.user.ownership_proof and not (doc or request.user.kyc_document):
            errors.append('Please upload a land ownership proof document or include it in your ID upload.')

        # Validate Barua ya Serikali
        if not govt_doc and not request.user.govt_letter:
            errors.append('Please upload a letter from your Local Government (Barua ya Serikali za Mtaa).')
        elif govt_doc:
            if govt_doc.content_type not in allowed:
                errors.append('Govt letter: use JPG, PNG, WebP, or PDF only.')
            elif govt_doc.size > 10 * 1024 * 1024:
                errors.append('Govt letter must be under 10 MB.')

        # Validate govt letter date — must be within last 2 months
        if govt_date_str:
            try:
                from datetime import datetime
                govt_date = datetime.strptime(govt_date_str, '%Y-%m-%d').date()
                two_months_ago = date.today() - timedelta(days=62)
                if govt_date < two_months_ago:
                    errors.append('The Government letter must be dated within the last 2 months. Please obtain a recent letter.')
                elif govt_date > date.today():
                    errors.append('Government letter date cannot be in the future.')
            except ValueError:
                errors.append('Invalid government letter date.')
        elif not request.user.govt_letter_date:
            errors.append('Please enter the date on your government letter.')

        if errors:
            for e in errors:
                messages.error(request, e)
            return redirect('accounts:profile_edit')

        # Save
        if doc:
            request.user.kyc_document = doc
        if ownership_doc:
            request.user.ownership_proof = ownership_doc
        if govt_doc:
            request.user.govt_letter = govt_doc
        if govt_date_str:
            from datetime import datetime
            request.user.govt_letter_date = datetime.strptime(govt_date_str, '%Y-%m-%d').date()
        request.user.kyc_status = 'pending'
        request.user.save()
        messages.success(request, '✅ Documents submitted! Admin will review within 24–48 hours.')
        return redirect('accounts:profile_edit')
    return redirect('accounts:profile_edit')


@admin_required
@require_http_methods(['POST'])
def review_kyc(request, user_id):
    from django.views.decorators.http import require_http_methods
    target = get_object_or_404(User, pk=user_id)
    action = request.POST.get('action')
    notes  = request.POST.get('kyc_notes', '').strip()
    if action == 'approve_kyc':
        target.kyc_status  = 'approved'
        target.is_verified = True
        target.kyc_notes   = notes
        target.save()
        messages.success(request, f'{target.username} KYC approved and account verified.')
    elif action == 'reject_kyc':
        target.kyc_status = 'rejected'
        target.kyc_notes  = notes or 'Document unclear or invalid. Please resubmit.'
        target.save()
        messages.warning(request, f'{target.username} KYC rejected.')
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
