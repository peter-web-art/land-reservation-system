from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django import forms
from django.utils.html import strip_tags
from django.db.models import Count, Q
import bleach, re

try:
    from django_ratelimit.decorators import ratelimit
except ImportError:
    def ratelimit(*args, **kwargs):
        def decorator(func): return func
        return decorator

from .models import User


def sanitize(value, max_length=None):
    if not value:
        return value
    cleaned = bleach.clean(value, tags=[], strip=True)
    cleaned = strip_tags(cleaned).strip()
    if max_length:
        cleaned = cleaned[:max_length]
    return cleaned


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
            field.widget.attrs.update({'class': 'form-control'})

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
            field.widget.attrs.update({'class': 'form-control'})

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
def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f'Welcome, {user.username}! Your account has been created.')
            next_url = request.POST.get('next') or request.GET.get('next') or ''
            from django.utils.http import url_has_allowed_host_and_scheme
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect('lands:customer_dashboard')
        # Return JSON for modal
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            errors = {f: e.as_text() for f, e in form.errors.items()}
            from django.http import JsonResponse
            return JsonResponse({'success': False, 'errors': errors}, status=400)
    else:
        form = UserRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})


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

def admin_required(view_func):
    """Decorator: only users with role=admin or is_staff can access."""
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not (request.user.is_staff or request.user.role == User.ROLE_ADMIN):
            messages.error(request, 'Access denied — Admin only.')
            return redirect('lands:land_list')
        return view_func(request, *args, **kwargs)
    return wrapper


@admin_required
def admin_portal(request):
    from lands.models import Land, Reservation
    total_users    = User.objects.count()
    total_owners   = User.objects.filter(role=User.ROLE_OWNER).count()
    total_customers = User.objects.filter(role=User.ROLE_CUSTOMER).count()
    unverified     = User.objects.filter(role=User.ROLE_OWNER, is_verified=False).count()
    suspended      = User.objects.filter(is_suspended=True).count()
    total_lands    = Land.objects.count()
    total_bookings = Reservation.objects.count()
    pending_book   = Reservation.objects.filter(status='pending').count()
    approved_book  = Reservation.objects.filter(status='approved').count()

    kyc_pending    = User.objects.filter(kyc_status='pending').order_by('-date_joined')
    flagged        = User.objects.filter(is_suspended=True)[:10]

    recent_lands   = Land.objects.select_related('owner').order_by('-created_at')[:15]
    recent_bookings = Reservation.objects.select_related('land', 'customer').order_by('-booking_date')[:15]

    return render(request, 'accounts/admin_portal.html', {
        'total_users': total_users, 'total_owners': total_owners,
        'total_customers': total_customers,
        'unverified': unverified, 'suspended': suspended,
        'total_lands': total_lands, 'total_bookings': total_bookings,
        'pending_book': pending_book, 'approved_book': approved_book,
        'kyc_pending': kyc_pending,
        'recent_users': User.objects.order_by('-date_joined')[:20],
        'recent_owners': User.objects.filter(role=User.ROLE_OWNER).order_by('-date_joined')[:20],
        'flagged': flagged,
        'recent_lands': recent_lands,
        'recent_bookings': recent_bookings,
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
    elif action == 'delete_user':
        if target.is_staff or target.role == User.ROLE_ADMIN:
            messages.error(request, 'Cannot delete admin users.')
        else:
            username = target.username
            target.delete()
            messages.success(request, f'{username} has been permanently deleted.')

    return redirect('accounts:admin_portal')


# ── KYC Views ─────────────────────────────────────────────────────────────────

@login_required
def submit_kyc(request):
    if request.method == 'POST':
        from datetime import date, timedelta
        doc       = request.FILES.get('kyc_document')
        govt_doc  = request.FILES.get('govt_letter')
        govt_date_str = request.POST.get('govt_letter_date', '').strip()
        allowed = ['image/jpeg','image/png','image/webp','application/pdf']
        errors = []

        # Validate KYC doc
        if not doc and not request.user.kyc_document:
            errors.append('Please upload your ID and land ownership document.')
        elif doc:
            if doc.content_type not in allowed:
                errors.append('KYC doc: use JPG, PNG, WebP, or PDF only.')
            elif doc.size > 10 * 1024 * 1024:
                errors.append('KYC doc must be under 10 MB.')

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
