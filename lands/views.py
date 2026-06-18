from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django import forms
from django.http import JsonResponse
from django.db.models import Q, F, Sum, Count
from django.conf import settings
from django.utils import timezone
from django.utils.html import strip_tags, format_html
from django.utils.http import url_has_allowed_host_and_scheme
from django.core.paginator import Paginator
from django.urls import reverse
from accounts.decorators import owner_required, customer_required, admin_required
import bleach, re
from datetime import date as date_cls, timedelta
from decimal import Decimal

from .models import Land, Reservation, PaymentRecord, Message, Wishlist, Notification, Utility, LandImage, LandReport
import json
from accounts.models import SystemSettings
from accounts.models import SystemSettings, OperatorPaymentConfig

User = get_user_model()

try:
    from django_ratelimit.decorators import ratelimit
except ImportError:
    def ratelimit(*args, **kwargs):
        def decorator(func): return func
        return decorator


# ── Notifications Helper ───────────────────────────────────────────────────────

def create_notification(user, notification_type, title, message, link=''):
    """Helper to create notifications for users."""
    from lands.models import Notification
    Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link
    )


def notify_admins(notification_type, title, message, link=''):
    """Send a notification to every active admin/staff account."""
    admin_users = User.objects.filter(Q(is_staff=True) | Q(role=User.ROLE_ADMIN), is_active=True)
    for admin in admin_users:
        create_notification(admin, notification_type, title, message, link)


def get_platform_fee_percentage():
    settings_obj = SystemSettings.objects.first()
    if not settings_obj:
        settings_obj = SystemSettings.objects.create()
    return settings_obj.platform_fee_percentage or Decimal('0')


def apply_platform_fee(payment):
    fee_rate = get_platform_fee_percentage()
    payment.platform_fee_rate = fee_rate
    payment.platform_fee_amount = round((payment.amount or Decimal('0')) * fee_rate / Decimal('100'), 2)
    return payment


# ── Helpers ───────────────────────────────────────────────────────────────────

def sanitize_text(value, max_length=None):
    if not value:
        return value
    cleaned = bleach.clean(value, tags=[], strip=True)
    cleaned = strip_tags(cleaned).strip()
    if max_length:
        cleaned = cleaned[:max_length]
    return cleaned


def validate_land_gallery_submission(request, existing_positions=None):
    if request.POST.get('save_draft') == 'true':
        return None

    uploaded_images = request.FILES.getlist('gallery_images')
    uploaded_positions = request.POST.getlist('image_positions')
    existing_positions = list(existing_positions or [])

    if not uploaded_images:
        total_images = len(existing_positions)
        if total_images < 3:
            return f'At least 3 photos are required. You currently have {total_images} photo(s).'
        if len(set(existing_positions)) != len(existing_positions):
            return 'Choose different viewing directions for each photo.'
        return None

    if len(uploaded_images) != len(uploaded_positions):
        return 'Each photo must include both an image and a viewing direction.'

    if any(not position for position in uploaded_positions):
        return 'Choose a viewing direction for every uploaded photo.'

    combined_positions = existing_positions + uploaded_positions
    total_images = len(existing_positions) + len(uploaded_images)

    if total_images < 3:
        return f'At least 3 photos are required. You currently have {total_images} photo(s).'

    if len(set(combined_positions)) != len(combined_positions):
        return 'Choose different viewing directions for each photo.'

    return None


def safe_redirect(request, target_url, fallback, **kwargs):
    if target_url and url_has_allowed_host_and_scheme(
        target_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(target_url)
    return redirect(fallback, **kwargs)


def send_sms_notification(phone_number, message):
    import logging
    logger = logging.getLogger(__name__)
    
    if not phone_number:
        logger.warning("SMS notification skipped: no phone number provided")
        return False
    
    if not all([settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_PHONE_NUMBER]):
        logger.info(f"SMS notification (Twilio not configured): {phone_number} - {message[:50]}...")
        return False
    
    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(body=message, from_=settings.TWILIO_PHONE_NUMBER, to=phone_number)
        logger.info(f"SMS sent successfully to {phone_number}")
        return True
    except Exception as e:
        logger.error(f"SMS failed for {phone_number}: {e}")
        return False


# ── Forms ─────────────────────────────────────────────────────────────────────

class LandForm(forms.ModelForm):
    owner_will_refund = forms.TypedChoiceField(
        choices=((True, 'Owner will refund'), (False, 'Owner will not refund')),
        coerce=lambda v: (v == 'True' or v is True),
        widget=forms.RadioSelect,
        initial=True,
        label='Refund policy'
    )

    class Meta:
        model  = Land
        fields = ['land_id', 'title', 'description', 'price', 'price_unit',
                  'region', 'district', 'ward', 'street',
                  'latitude', 'longitude',
                  'usage', 'size', 'size_unit', 'land_use',
                  'topography', 'soil_fertility', 'utilities', 'additional_utilities_notes',
                  'weekly_discount', 'monthly_discount',
                  'contact_phone', 'contact_email', 'land_image_path', 'wizard_step', 'owner_will_refund']

    def __init__(self, *args, **kwargs):
        self.is_draft = kwargs.pop('is_draft', False)
        super().__init__(*args, **kwargs)
        self.fields['utilities'].widget = forms.CheckboxSelectMultiple()
        self.fields['utilities'].queryset = Utility.objects.all()
        # District is populated dynamically via JS, so use a plain text-like select
        self.fields['district'].widget = forms.Select(choices=[('', '-- Chagua Wilaya --')])
        self.fields['description'].required = False
        self.fields['additional_utilities_notes'].required = False
        self.fields['land_id'].required = False
        self.fields['land_image_path'].required = False
        self.fields['wizard_step'].required = False

        if self.is_draft:
            # If saving as draft, only title is strictly required
            for field_name, field in self.fields.items():
                if field_name != 'title':
                    field.required = False

        if self.instance and self.instance.pk:
            self.fields['land_id'].widget.attrs.update({
                'readonly': 'readonly',
                'class': 'w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-lg text-sm text-gray-900 cursor-not-allowed',
            })
        else:
            self.fields['land_id'].widget = forms.HiddenInput()
        submitted_region = self.data.get(self.add_prefix('region')) if self.is_bound else None
        region_for_districts = submitted_region or (
            self.instance.region if self.instance and self.instance.pk else None
        )
        if region_for_districts:
            from .tanzania_locations import get_districts_for_region
            districts = get_districts_for_region(region_for_districts)
            choices = [('', '-- Chagua Wilaya --')] + [(d, d) for d in districts]
            self.fields['district'].widget = forms.Select(choices=choices)
        owner = getattr(self.instance, 'owner', None)
        if owner:
            self.fields['contact_phone'].initial = getattr(owner, 'phone', '')
            self.fields['contact_email'].initial = getattr(owner, 'email', '')
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'w-full px-4 py-3 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#1a5c38]/30 focus:border-[#1a5c38] transition-colors'})
        self.fields['region'].widget.attrs['id'] = 'id_region'
        self.fields['district'].widget.attrs['id'] = 'id_district'
        self.fields['ward'].widget.attrs['placeholder'] = 'e.g. Kata ya Msasani'
        self.fields['street'].widget.attrs['placeholder'] = 'e.g. Mtaa wa Kimara'
        self.fields['price'].widget.attrs['placeholder']            = 'e.g. 150000'
        self.fields['weekly_discount'].widget.attrs['placeholder']  = 'e.g. 10  (means 10% off)'
        self.fields['monthly_discount'].widget.attrs['placeholder'] = 'e.g. 20  (means 20% off)'

    def clean_title(self):        return sanitize_text(self.cleaned_data.get('title'), 200)
    def clean_description(self):  return sanitize_text(self.cleaned_data.get('description'))
    def clean_ward(self):         return sanitize_text(self.cleaned_data.get('ward'), 100)

    def clean_land_image_path(self):
        image = self.cleaned_data.get('land_image_path')
        if image and hasattr(image, 'content_type'):
            if image.content_type not in ['image/jpeg', 'image/png', 'image/webp']:
                raise forms.ValidationError('Use JPG, PNG, or WebP only.')
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Max file size is 5 MB.')
        return image

    def clean(self):
        cleaned      = super().clean()
        usage = cleaned.get('usage')
        wd = cleaned.get('weekly_discount', 0) or 0
        md = cleaned.get('monthly_discount', 0) or 0
        if wd and not (0 <= wd <= 90):
            self.add_error('weekly_discount', 'Must be 0–90%.')
        if md and not (0 <= md <= 90):
            self.add_error('monthly_discount', 'Must be 0–90%.')
        if usage == 'sale':
            cleaned['price_unit']        = 'total'
            cleaned['weekly_discount']   = 0
            cleaned['monthly_discount']  = 0
        return cleaned


class SearchForm(forms.Form):
    location  = forms.CharField(max_length=200, required=False)
    min_price = forms.DecimalField(required=False, decimal_places=2)
    max_price = forms.DecimalField(required=False, decimal_places=2)
    min_size  = forms.DecimalField(required=False, decimal_places=2, help_text='Minimum land size')
    max_size  = forms.DecimalField(required=False, decimal_places=2, help_text='Maximum land size')
    land_use  = forms.ChoiceField(choices=[('', 'Any')] + Land.LAND_TYPE_CHOICES, required=False)
    keyword   = forms.CharField(max_length=200, required=False)

    def clean_keyword(self):   return sanitize_text(self.cleaned_data.get('keyword'), 200)
    def clean_location(self):  return sanitize_text(self.cleaned_data.get('location'), 200)
    def clean_min_price(self):
        v = self.cleaned_data.get('min_price')
        if v is not None and v < 0: raise forms.ValidationError('Must be positive.')
        return v
    def clean_max_price(self):
        v = self.cleaned_data.get('max_price')
        if v is not None and v < 0: raise forms.ValidationError('Must be positive.')
        return v
    def clean_min_size(self):
        v = self.cleaned_data.get('min_size')
        if v is not None and v < 0: raise forms.ValidationError('Must be positive.')
        return v
    def clean_max_size(self):
        v = self.cleaned_data.get('max_size')
        if v is not None and v < 0: raise forms.ValidationError('Must be positive.')
        return v


class ReservationForm(forms.ModelForm):
    start_date = forms.DateField(required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    end_date = forms.DateField(required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))

    class Meta:
        model  = Reservation
        fields = ['customer_name', 'customer_email', 'customer_phone',
                  'start_date', 'end_date', 'requested_size', 'payment_method', 'payment_reference', 'notes']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.land = kwargs.pop('land', None)
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full px-4 py-3 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#1a5c38]/30 focus:border-[#1a5c38] transition-colors'
            })
        self.fields['notes'].widget = forms.Textarea(attrs={
            'rows': 2, 'class': 'w-full px-4 py-3 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#1a5c38]/30 focus:border-[#1a5c38] transition-colors',
            'placeholder': 'Any specific requirements, access instructions, or notes…'})
        
        if self.land and self.land.size:
            self.fields['requested_size'].widget.attrs['placeholder'] = f"e.g. 5 (Max {self.land.size})"
            self.fields['requested_size'].label = f"Requested Size ({self.land.get_size_unit_display()})"
        else:
            self.fields['requested_size'].widget = forms.HiddenInput()
        self.fields['payment_reference'].widget.attrs['placeholder'] = 'e.g. M-Pesa: ABC123XY'
        today_str = date_cls.today().isoformat()
        self.fields['start_date'].widget.attrs['min'] = today_str
        self.fields['end_date'].widget.attrs['min']   = today_str
        if self.land and self.land.usage == 'sale':
            self.fields['start_date'].required = False
            self.fields['end_date'].required   = False
        elif self.land and self.land.usage == 'rent':
            self.fields['start_date'].required = True
            self.fields['end_date'].required   = True
        if self.user and self.user.is_authenticated:
            self.fields['customer_name'].initial  = self.user.get_full_name() or self.user.username
            self.fields['customer_email'].initial = self.user.email
            self.fields['customer_phone'].initial = getattr(self.user, 'phone', '')
            self.fields['customer_name'].widget   = forms.HiddenInput()
            self.fields['customer_email'].widget  = forms.HiddenInput()

    def clean_customer_phone(self):
        p = self.cleaned_data.get('customer_phone') or ''
        p = p.strip()
        if p and not re.match(r'^[\d\+\s\-\(\)]{6,20}$', p):
            raise forms.ValidationError('Enter a valid phone number.')
        return p

    def clean(self):
        cleaned = super().clean()
        start   = cleaned.get('start_date')
        end     = cleaned.get('end_date')
        req_size = cleaned.get('requested_size')
        
        if self.land and self.land.size and req_size:
            if req_size <= 0:
                self.add_error('requested_size', 'Size must be greater than zero.')
        
        if self.land and self.land.usage == 'rent':
            if not start:
                self.add_error('start_date', 'Select a start date.')
            if not end:
                self.add_error('end_date', 'Select an end date.')
            if start and end:
                if end <= start:
                    self.add_error('end_date', 'End date must be after start date.')
                elif start < date_cls.today():
                    self.add_error('start_date', 'Start date cannot be in the past.')
                else:
                    if not self.land.is_available_for_dates(start, end, req_size):
                        remain = self.land.get_remaining_size_for_dates(start, end)
                        self.add_error('requested_size',
                            f'Only {remain} {self.land.get_size_unit_display()} available for these dates.')
        elif self.land and self.land.usage == 'sale':
            if not self.land.is_available_for_dates(requested_size=req_size):
                remain = self.land.get_remaining_size_for_dates()
                self.add_error('requested_size',
                    f'Only {remain} {self.land.get_size_unit_display()} available for sale.')
        return cleaned


class PaymentSubmissionForm(forms.ModelForm):
    class Meta:
        model = PaymentRecord
        fields = ['amount', 'payment_method', 'payment_reference', 'payment_receipt', 'payment_date', 'notes']
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional: Add any extra details about your payment...'}),
        }

    def __init__(self, *args, **kwargs):
        self.reservation = kwargs.pop('reservation', None)
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'w-full px-4 py-3 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#1a5c38]/30 focus:border-[#1a5c38] transition-colors'})
        self.fields['amount'].widget.attrs['placeholder'] = 'e.g. 150000'
        self.fields['payment_reference'].required = True
        self.fields['payment_date'].required = True
        self.fields['amount'].required = True

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is None or amount <= 0:
            raise forms.ValidationError('Enter a valid payment amount.')
        if self.reservation and amount > self.reservation.remaining_balance:
            raise forms.ValidationError(f'Amount cannot exceed remaining balance of Tsh {self.reservation.remaining_balance}.')
        return amount

@login_required
def reservation_payment_options(request, pk):
    """Allow customer to view available operator payment methods and choose one for a reservation."""
    reservation = get_object_or_404(Reservation, pk=pk)
    if request.user != reservation.customer:
        messages.error(request, 'You are not authorized to view payment options for this reservation.')
        return redirect('lands:my_reservations')

    configs = OperatorPaymentConfig.objects.filter(is_active=True).order_by('priority')

    if request.method == 'POST':
        try:
            config_id = int(request.POST.get('payment_config'))
            config = OperatorPaymentConfig.objects.get(pk=config_id, is_active=True)
            reservation.selected_operator_payment = config
            reservation.save()
            messages.success(request, 'Payment method selection saved. Please follow the instructions to complete your payment.')
            return redirect('lands:my_reservations')
        except Exception:
            messages.error(request, 'Invalid selection.')

    return render(request, 'lands/reservation_payment_options.html', {
        'reservation': reservation,
        'configs': configs,
    })


# ── Views ─────────────────────────────────────────────────────────────────────

def land_list(request):
    lands = Land.objects.filter(is_active=True, is_draft=False).select_related('owner').order_by('-created_on')
    
    # ── Filters from hero search bar & category tabs ──
    usage = request.GET.get('type')
    land_use     = request.GET.get('use')
    location     = request.GET.get('location')
    keyword      = request.GET.get('keyword', '')
    min_price    = request.GET.get('min_price')
    max_price    = request.GET.get('max_price')
    min_size     = request.GET.get('min_size')
    max_size     = request.GET.get('max_size')
    availability = request.GET.get('availability')
    
    if usage in ['rent', 'sale']:
        lands = lands.filter(usage=usage)
    if land_use in ['agricultural', 'residential', 'commercial', 'industrial', 'mixed']:
        lands = lands.filter(land_use=land_use)
    if location:
        lands = lands.filter(Q(location__icontains=location) | Q(title__icontains=location) | Q(description__icontains=location))
    if keyword:
        lands = lands.filter(Q(title__icontains=keyword) | Q(description__icontains=keyword))
    if min_price:
        try:
            lands = lands.filter(price__gte=float(min_price))
        except (ValueError, TypeError):
            pass
    if max_price:
        try:
            lands = lands.filter(price__lte=float(max_price))
        except (ValueError, TypeError):
            pass
    if min_size:
        try:
            lands = lands.filter(size__gte=float(min_size))
        except (ValueError, TypeError):
            pass
    if max_size:
        try:
            lands = lands.filter(size__lte=float(max_size))
        except (ValueError, TypeError):
            pass
    
    # FIX #2: Sorting must happen BEFORE availability filter (which converts QS → list)
    sort = request.GET.get('sort', 'newest')
    if sort == 'price_low':
        lands = lands.order_by('price')
    elif sort == 'price_high':
        lands = lands.order_by('-price')
    elif sort == 'size_large':
        lands = lands.order_by(F('size').desc(nulls_last=True))
    else:
        lands = lands.order_by('-created_on')

    # FIX #3: Build map_pins from queryset BEFORE converting to list via availability filter
    map_pins_qs = lands.filter(latitude__isnull=False, longitude__isnull=False)
    if availability == 'available':
        map_pins_qs = [l for l in map_pins_qs if l.is_available]
    elif availability in ['reserved', 'unavailable']:
        map_pins_qs = [l for l in map_pins_qs if not l.is_available]
    map_pins = json.dumps([
        {'id': l.id, 'title': l.title, 'lat': l.latitude, 'lng': l.longitude,
         'price': l.price_display, 'location': l.location, 'type': l.usage,
         'status': l.availability_state,
         'availability_label': l.availability_label,
         'remaining_size': str(l.current_remaining_size),
         'total_size': str(l.size) if l.size is not None else ''}
        for l in map_pins_qs[:200]
    ])

    # Availability filter (may convert queryset → list — must happen after sort & map_pins)
    if availability == 'available':
        lands = [l for l in lands if l.is_available]
    elif availability in ['reserved', 'unavailable']:
        lands = [l for l in lands if not l.is_available]

    paginator = Paginator(lands, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    wishlisted_ids = []
    if request.user.is_authenticated:
        wishlisted_ids = list(Wishlist.objects.filter(user=request.user).values_list('land_id', flat=True))
    
    # Tanzania regions for autocomplete
    tanzania_regions = [
        'Dar es Salaam', 'Arusha', 'Mwanza', 'Dodoma', 'Morogoro', 'Mbeya',
        'Tanga', 'Kilimanjaro', 'Kagera', 'Kigoma', 'Lindi', 'Mara', 'Mtwara',
        'Pwani', 'Rukwa', 'Ruvuma', 'Shinyanga', 'Singida', 'Songwe', 'Tabora',
        'Simiyu', 'Geita', 'Katavi', 'Njombe', 'Iringa', 'Manyara'
    ]

    featured_lands = Land.objects.filter(is_active=True).select_related('owner').order_by('-created_on')
    
    return render(request, 'lands/land_list.html', {
        'lands': page_obj, 'page_obj': page_obj, 'paginator': paginator,
        'map_pins': map_pins, 'wishlisted_ids': wishlisted_ids,
        'featured_lands': featured_lands,
        'tanzania_regions': tanzania_regions,
        'current_filters': {
            'usage': usage,
            'land_use': land_use,
            'location': location,
            'keyword': keyword,
            'min_price': min_price,
            'max_price': max_price,
            'min_size': min_size,
            'max_size': max_size,
            'availability': availability,
            'sort': request.GET.get('sort', 'newest'),
        },
        'show_login_prompt': False,
    })


def browse_lands(request):
    """Simplified listing page for browsing all land posts (no homepage sections).
    Intended as a direct 'browse' landing where users can scan listings only.
    """
    lands_qs = Land.objects.filter(is_active=True, is_draft=False).select_related('owner').order_by('-created_on')

    # Basic filters supported on browse page (keyword, location)
    keyword = request.GET.get('keyword', '')
    location = request.GET.get('location', '')
    if keyword:
        lands_qs = lands_qs.filter(Q(title__icontains=keyword) | Q(description__icontains=keyword))
    if location:
        lands_qs = lands_qs.filter(Q(location__icontains=location) | Q(title__icontains=location))

    paginator = Paginator(lands_qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    wishlisted_ids = []
    if request.user.is_authenticated:
        wishlisted_ids = list(Wishlist.objects.filter(user=request.user).values_list('land_id', flat=True))

    return render(request, 'lands/browse.html', {
        'lands': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'wishlisted_ids': wishlisted_ids,
        'show_login_prompt': False,
    })


def location_autocomplete(request):
    """API endpoint for location autocomplete suggestions."""
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'suggestions': []})
    
    tanzania_regions = [
        'Dar es Salaam', 'Arusha', 'Mwanza', 'Dodoma', 'Morogoro', 'Mbeya',
        'Tanga', 'Kilimanjaro', 'Kagera', 'Kigoma', 'Lindi', 'Mara', 'Mtwara',
        'Pwani', 'Rukwa', 'Ruvuma', 'Shinyanga', 'Singida', 'Songwe', 'Tabora',
        'Simiyu', 'Geita', 'Katavi', 'Njombe', 'Iringa', 'Manyara'
    ]
    
    # Get locations from database
    db_locations = Land.objects.filter(
        location__icontains=query, is_active=True
    ).values_list('location', flat=True).distinct()[:10]
    
    suggestions = []
    query_lower = query.lower()
    
    # Add region matches
    for region in tanzania_regions:
        if query_lower in region.lower():
            suggestions.append({'value': region, 'type': 'region'})
    
    # Add database location matches
    for loc in db_locations:
        if loc and loc not in [s['value'] for s in suggestions]:
            suggestions.append({'value': loc, 'type': 'listing'})
    
    # Add keyword matches from land titles
    lands = Land.objects.filter(
        Q(title__icontains=query) | Q(location__icontains=query),
        is_active=True
    ).values_list('location', flat=True).distinct()[:5]
    
    for loc in lands:
        if loc and loc not in [s['value'] for s in suggestions]:
            suggestions.append({'value': loc, 'type': 'match'})
    
    return JsonResponse({'suggestions': suggestions[:10]})


def districts_api(request):
    """Return districts for a given region (for cascading dropdown)."""
    from .tanzania_locations import get_districts_for_region
    region = request.GET.get('region', '').strip()
    districts = get_districts_for_region(region)
    return JsonResponse({'districts': districts})


@ratelimit(key='ip', rate='30/m', method='GET', block=True)
def search_lands(request):
    form  = SearchForm(request.GET)
    lands = Land.objects.filter(is_active=True).select_related('owner').order_by('-created_on')
    
    # Handle usage filter from navbar (rent/sale)
    usage = request.GET.get('usage')
    if usage in ['rent', 'sale']:
        lands = lands.filter(usage=usage)
    
    # Handle land_use filter (agricultural, residential, etc.)
    land_use = request.GET.get('land_use')
    if land_use in ['agricultural', 'residential', 'commercial', 'industrial', 'mixed']:
        lands = lands.filter(land_use=land_use)
    
    # Handle availability filter
    availability = request.GET.get('availability')
    
    if form.is_valid():
        loc = form.cleaned_data.get('location')
        mn  = form.cleaned_data.get('min_price')
        mx  = form.cleaned_data.get('max_price')
        min_s = form.cleaned_data.get('min_size')
        max_s = form.cleaned_data.get('max_size')
        kw  = form.cleaned_data.get('keyword')
        lu  = form.cleaned_data.get('land_use')
        
        if loc: lands = lands.filter(Q(location__icontains=loc) | Q(title__icontains=loc) | Q(description__icontains=loc))
        if mn is not None: lands = lands.filter(price__gte=mn)
        if mx is not None: lands = lands.filter(price__lte=mx)
        if min_s is not None: lands = lands.filter(size__gte=min_s)
        if max_s is not None: lands = lands.filter(size__lte=max_s)
        if kw:  lands = lands.filter(Q(title__icontains=kw) | Q(description__icontains=kw))
        if lu:  lands = lands.filter(land_use=lu)
    
    # FIX #2: Sort BEFORE availability filter to avoid calling .order_by() on a list
    sort = request.GET.get('sort', 'newest')
    if sort == 'price_low':
        lands = lands.order_by('price')
    elif sort == 'price_high':
        lands = lands.order_by('-price')
    elif sort == 'size_large':
        lands = lands.order_by(F('size').desc(nulls_last=True))
    else:
        lands = lands.order_by('-created_on')

    # FIX #3: Build map_pins from queryset BEFORE converting to list
    map_pins_qs = lands.filter(latitude__isnull=False, longitude__isnull=False)
    if availability == 'available':
        map_pins_qs = [l for l in map_pins_qs if l.is_available]
    elif availability in ['reserved', 'unavailable']:
        map_pins_qs = [l for l in map_pins_qs if not l.is_available]
    map_pins = json.dumps([
        {'id': l.id, 'title': l.title, 'lat': l.latitude, 'lng': l.longitude,
         'price': l.price_display, 'location': l.location, 'type': l.usage,
         'status': l.availability_state,
         'availability_label': l.availability_label,
         'remaining_size': str(l.current_remaining_size),
         'total_size': str(l.size) if l.size is not None else ''}
        for l in map_pins_qs[:200]
    ])

    # Availability filter (may convert QS → list — must happen after sort & map_pins)
    if availability == 'available':
        lands = [l for l in lands if l.is_available]
    elif availability in ['reserved', 'unavailable']:
        lands = [l for l in lands if not l.is_available]

    paginator = Paginator(lands, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    wishlisted_ids = []
    if request.user.is_authenticated:
        wishlisted_ids = list(Wishlist.objects.filter(user=request.user).values_list('land_id', flat=True))
    
    # Tanzania regions for autocomplete
    tanzania_regions = [
        'Dar es Salaam', 'Arusha', 'Mwanza', 'Dodoma', 'Morogoro', 'Mbeya',
        'Tanga', 'Kilimanjaro', 'Kagera', 'Kigoma', 'Lindi', 'Mara', 'Mtwara',
        'Pwani', 'Rukwa', 'Ruvuma', 'Shinyanga', 'Singida', 'Songwe', 'Tabora',
        'Simiyu', 'Geita', 'Katavi', 'Njombe', 'Iringa', 'Manyara'
    ]
    
    return render(request, 'lands/search_results.html', {
        'lands': page_obj, 'page_obj': page_obj, 'paginator': paginator,
        'form': form, 'searched_location': request.GET.get('location', ''),
        'map_pins': map_pins, 'tanzania_regions': tanzania_regions,
        'wishlisted_ids': wishlisted_ids,
        'show_login_prompt': False,
    })


def land_detail(request, pk):
    land = get_object_or_404(Land, pk=pk, is_active=True)
    Land.objects.filter(pk=pk).update(view_count=F('view_count') + 1)
    similar = (Land.objects.filter(is_active=True, location__icontains=land.location.split(',')[0])
               .exclude(pk=pk).select_related('owner')[:4])
    if similar.count() < 4:
        similar = (Land.objects.filter(is_active=True, land_use=land.land_use)
                   .exclude(pk=pk).select_related('owner')[:4])
    is_wishlisted = False
    if request.user.is_authenticated:
        is_wishlisted = Wishlist.objects.filter(user=request.user, land=land).exists()
        can_view_owner_contact = (
            request.user == land.owner or
            Reservation.objects.filter(
                land=land,
                customer=request.user,
                status='approved',
                payment_confirmed=True,
            ).exists()
        )
    else:
        can_view_owner_contact = False

    # Build booked periods for availability calendar
    booked_periods = []
    if land.usage == 'rent':
        for period in land.get_booked_periods():
            booked_periods.append({
                'start': period['start_date'].isoformat(),
                'end': period['end_date'].isoformat(),
                'status': period['status'],
            })

    # Build crop suggestions for agricultural/mixed land
    from .crop_suggestions import get_crop_suggestions
    crop_suggestions = get_crop_suggestions(
        location=land.location,
        soil_fertility=land.soil_fertility or 'moderate',
        topography=land.topography or 'flat',
        land_use=land.land_use or 'agricultural',
        region_key=land.region or None,
    )

    return render(request, 'lands/land_detail.html', {
        'land': land, 'similar_lands': similar, 'is_wishlisted': is_wishlisted,
        'can_view_owner_contact': can_view_owner_contact,
        'booked_periods_json': json.dumps(booked_periods),
        'next_available_date': land.next_available_date.isoformat(),
        'crop_suggestions': crop_suggestions,
        'crop_suggestions_json': json.dumps(crop_suggestions),
    })


def crop_suggestions_api(request, pk):
    """JSON API endpoint returning crop suggestions for a specific land."""
    land = get_object_or_404(Land, pk=pk, is_active=True)
    from .crop_suggestions import get_crop_suggestions
    suggestions = get_crop_suggestions(
        location=land.location,
        soil_fertility=land.soil_fertility or 'moderate',
        topography=land.topography or 'flat',
        land_use=land.land_use or 'agricultural',
        region_key=land.region or None,
    )
    return JsonResponse({
        'land_id': land.pk,
        'location': land.location,
        'soil_fertility': land.get_soil_fertility_display(),
        'topography': land.get_topography_display(),
        'land_use': land.get_land_use_display(),
        'suggestions': suggestions,
    })

@ratelimit(key='ip', rate='10/m', method='POST', block=True)
def book_land(request, pk):
    land = get_object_or_404(Land, pk=pk, is_active=True)

    # Prevent admin/staff accounts from booking land
    if request.user.is_authenticated and (request.user.role == User.ROLE_ADMIN or request.user.is_staff):
        messages.error(request, 'Admin accounts cannot book land.')
        return redirect('lands:land_detail', pk=land.pk)

    # FIX #1: prevent owner booking their own land
    if request.user.is_authenticated and request.user == land.owner:
        messages.warning(request, 'You cannot book your own listing.')
        return redirect('lands:land_detail', pk=land.pk)

    if land.usage == 'sale' and not land.is_available:
        messages.warning(request, 'This land has already been sold.')
        return redirect('lands:land_detail', pk=land.pk)

    initial   = {}
    qs_start  = request.GET.get('start')
    qs_end    = request.GET.get('end')
    if qs_start: initial['start_date'] = qs_start
    if qs_end:   initial['end_date']   = qs_end

    # Pre-fill dates with next available period if land is currently unavailable
    if land.usage == 'rent' and not land.is_available and not qs_start:
        next_date = land.next_available_date
        if next_date:
            initial['start_date'] = next_date.isoformat()
            if land.min_duration_days:
                end_date = next_date + timedelta(days=land.min_duration_days)
                initial['end_date'] = end_date.isoformat()

    if request.method == 'POST':
        form = ReservationForm(request.POST, user=request.user, land=land)
        if form.is_valid():
            # FIX #1b: duplicate active booking check (rent + sale)
            # BUG #4 FIX: Also check for guest users by email
            if request.user.is_authenticated:
                existing = Reservation.objects.filter(
                    land=land, customer=request.user,
                    status__in=['pending', 'awaiting_payment', 'approved']).exists()
                if existing:
                    messages.warning(request,
                        'You already have an active or pending booking for this land.')
                    return redirect('lands:land_detail', pk=land.pk)
            else:
                # Check guest duplicate bookings by email
                guest_email = form.cleaned_data.get('customer_email')
                if guest_email:
                    existing = Reservation.objects.filter(
                        land=land, customer_email=guest_email,
                        status__in=['pending', 'awaiting_payment', 'approved']).exists()
                    if existing:
                        messages.warning(request,
                            'A booking for this land already exists with this email address.')
                        return redirect('lands:land_detail', pk=land.pk)
            r            = form.save(commit=False)
            r.land       = land
            r.status     = 'pending'
            r.start_date = form.cleaned_data.get('start_date')
            r.end_date   = form.cleaned_data.get('end_date')
            r.requested_size = form.cleaned_data.get('requested_size')
            
            base_price = (land.calculate_price(r.start_date, r.end_date)
                              if r.start_date and r.end_date else land.price)
            if base_price is not None and r.requested_size and land.size:
                base_price = base_price * (Decimal(str(r.requested_size)) / land.size)
            r.agreed_price = round(base_price, 2) if base_price is not None else None
            
            if request.user.is_authenticated:
                r.customer = request.user
                if not r.customer_name:
                    r.customer_name = request.user.get_full_name() or request.user.username
                if not r.customer_email:
                    r.customer_email = request.user.email
            r.save()
            messages.success(request,
                '✅ Booking request submitted! The owner will review it shortly.')
            return redirect('lands:my_reservations') if request.user.is_authenticated \
                else redirect('lands:land_detail', pk=land.pk)
    else:
        form = ReservationForm(user=request.user, land=land, initial=initial)

    if land.price is None:
        price_per_day = 0.0
    elif land.price_unit == 'month':
        price_per_day = float(land.price / 30)
    elif land.price_unit == 'year':
        price_per_day = float(land.price / 365)
    else:
        price_per_day = float(land.price)

    return render(request, 'lands/book_land.html', {
        'land': land, 'form': form,
        'price_per_day': price_per_day,
        'weekly_discount':  float(land.weekly_discount),
        'monthly_discount': float(land.monthly_discount),
    })


@customer_required
@login_required
def my_reservations(request):
    reservations = (Reservation.objects
                    .filter(customer=request.user)
                    .select_related('land')
                    .order_by('-created_on'))
    return render(request, 'lands/my_reservations.html', {'reservations': reservations})


@login_required
@require_http_methods(['POST'])
def cancel_reservation(request, pk):
    r = get_object_or_404(Reservation, pk=pk, customer=request.user)
    if r.status in ['pending', 'awaiting_payment']:
        r.status = 'cancelled'
        r.save()
        messages.success(request, 'Pending reservation cancelled.')
    elif r.status == 'approved':
        # FIX #7: approved cancellations need confirmation + owner SMS
        r.status = 'cancelled'
        r.save()
        owner_phone = r.land.contact_phone or (r.land.owner.phone if r.land.owner else None)
        if owner_phone:
            send_sms_notification(owner_phone,
                f"⚠️ Customer {r.customer_name or r.customer.username} has CANCELLED "
                f"their approved booking for '{r.land.title}'.")
        messages.warning(request,
            'Your approved booking has been cancelled. The owner has been notified.')
    else:
        messages.error(request, 'This reservation cannot be cancelled.')
    return redirect('lands:my_reservations')


@customer_required
@login_required
def customer_dashboard(request):
    qs        = Reservation.objects.filter(customer=request.user)
    total     = qs.count()
    pending   = qs.filter(status='pending').count()
    awaiting_payment = qs.filter(status='awaiting_payment').count()
    approved  = qs.filter(status='approved').count()
    cancelled = qs.filter(status='cancelled').count()
    recent    = qs.select_related('land').order_by('-created_on')[:5]
    wishlist_count = Wishlist.objects.filter(user=request.user).count()
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('land', 'land__owner')[:4]
    featured_lands = Land.objects.filter(is_active=True).select_related('owner').order_by('-created_on')[:4]
    active_reservations = qs.filter(status__in=['pending', 'awaiting_payment', 'approved']).select_related('land', 'land__owner').order_by('-created_on')[:6]
    unread_notifications = Notification.objects.filter(user=request.user, is_read=False).count()
    latest_notifications = Notification.objects.filter(user=request.user).select_related('user')[:3]
    return render(request, 'lands/customer_dashboard.html', {
        'total': total, 'pending': pending,
        'approved': approved, 'awaiting_payment': awaiting_payment, 'cancelled': cancelled,
        'recent_reservations': recent,
        'active_reservations': active_reservations,
        'featured_lands': featured_lands,
        'wishlist_count': wishlist_count, 'wishlist_items': wishlist_items,
        'unread_notifications': unread_notifications,
        'latest_notifications': latest_notifications,
    })


# FIX #5: owner_required instead of just login_required
@owner_required
def owner_dashboard(request):
    from django.db.models import Sum
    from django.utils import timezone
    from datetime import timedelta
    
    # Contextual Filtering for Owner Dashboard
    keyword = request.GET.get('keyword', '')
    status = request.GET.get('status', '')  # 'published', 'draft'
    usage = request.GET.get('usage', '')    # 'rent', 'sale'

    lands = Land.objects.filter(owner=request.user).prefetch_related('reservations', 'images')
    
    if keyword:
        lands = lands.filter(Q(title__icontains=keyword) | Q(location__icontains=keyword) | Q(description__icontains=keyword))
    if status == 'published':
        lands = lands.filter(is_draft=False)
    elif status == 'draft':
        lands = lands.filter(is_draft=True)
    if usage in ['rent', 'sale']:
        lands = lands.filter(usage=usage)

    ids = lands.values_list('id', flat=True)
    
    # Separate drafts from published listings for the stats cards (using unfiltered set)
    all_lands = Land.objects.filter(owner=request.user)
    published_lands = all_lands.filter(is_draft=False)
    draft_lands     = all_lands.filter(is_draft=True)
    
    pending_count  = Reservation.objects.filter(land_id__in=ids, status='pending').count()
    approved_count = Reservation.objects.filter(land_id__in=ids, status='approved').count()
    available_count = sum(1 for l in published_lands if l.is_available)
    recent_bookings = (Reservation.objects
                       .filter(land_id__in=ids)
                       .select_related('land', 'customer')
                       .order_by('-created_on')[:8])
    total_views = sum(l.view_count for l in lands)
    total_wishlists = Wishlist.objects.filter(land__in=lands).count()
    
    # Earnings calculations
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)
    seven_days_ago = today - timedelta(days=7)
    
    # This month's earnings
    monthly_earnings = Reservation.objects.filter(
        land_id__in=ids,
        status='approved',
        payment_status='paid',
        created_on__gte=thirty_days_ago,
    ).aggregate(total=Sum('amount_paid'))['total'] or 0
    
    # Last 7 days earnings
    weekly_earnings = Reservation.objects.filter(
        land_id__in=ids,
        status='approved',
        payment_status='paid',
        created_on__gte=seven_days_ago
    ).aggregate(total=Sum('amount_paid'))['total'] or 0
    
    # All time earnings
    total_earnings = Reservation.objects.filter(
        land_id__in=ids,
        status='approved',
        payment_status='paid'
    ).aggregate(total=Sum('amount_paid'))['total'] or 0
    
    # Booking count stats
    total_bookings = Reservation.objects.filter(land_id__in=ids, status='approved').count()
    
    return render(request, 'lands/dashboard.html', {
        'lands': lands,
        'draft_count': draft_lands.count(),
        'published_count': published_lands.count(),
        'pending_count': pending_count,
        'approved_count': approved_count,
        'available_count': available_count,
        'recent_bookings': recent_bookings,
        'total_views': total_views,
        'total_wishlists': total_wishlists,
        'monthly_earnings': monthly_earnings,
        'weekly_earnings': weekly_earnings,
        'total_earnings': total_earnings,
        'total_bookings': total_bookings,
        'today': today,
    })


# FIX #4: owner_required
@owner_required
@ratelimit(key='user', rate='20/m', method='POST', block=True)
def add_land(request):
    # Check if owner is verified before allowing land posting
    if request.user.is_authenticated and request.user.role == 'owner':
        if not request.user.is_verified:
            messages.error(request, 'Your account must be verified by the operator before you can post lands. Please contact support or wait for verification.')
            return redirect('lands:owner_dashboard')
    
    initial_step = 1
    if request.method == 'POST':
        initial_step = int(request.POST.get('current_step', 1) or 1)
        is_draft = request.POST.get('save_draft') == 'true'
        form = LandForm(request.POST, request.FILES, is_draft=is_draft)
        if form.is_valid():
            gallery_error = validate_land_gallery_submission(request)
            if gallery_error:
                form.add_error(None, gallery_error)
            else:
                land       = form.save(commit=False)
                land.owner = request.user
                is_draft = request.POST.get('save_draft') == 'true'
                land.is_draft = is_draft
                land.wizard_step = initial_step
                land.save()
                form.save_m2m()

                # Handle multiple images
                images = request.FILES.getlist('gallery_images')
                positions = request.POST.getlist('image_positions')
                
                for i, img in enumerate(images):
                    pos = positions[i]
                    LandImage.objects.create(
                        land=land,
                        image=img,
                        position=pos,
                        is_primary=(i == 0 and not land.land_image_path),
                        order=i
                    )

                if is_draft:
                    messages.success(request, f'"{land.title}" saved as draft.')
                else:
                    messages.success(request, f'"{land.title}" published successfully.')
                return redirect('lands:owner_dashboard')
    else:
        initial = {
            'contact_phone': getattr(request.user, 'phone', ''),
            'contact_email': request.user.email,
        }
        form = LandForm(initial=initial)
    return render(request, 'lands/add_land.html', {'form': form, 'land': None, 'initial_step': initial_step})


# FIX #4: owner_required
@owner_required
@ratelimit(key='user', rate='20/m', method='POST', block=True)
def edit_land(request, pk):
    land = get_object_or_404(Land, pk=pk, owner=request.user)
    initial_step = land.wizard_step
    if request.method == 'POST':
        initial_step = int(request.POST.get('current_step', land.wizard_step) or land.wizard_step)
        is_draft = request.POST.get('save_draft') == 'true'
        form = LandForm(request.POST, request.FILES, instance=land, is_draft=is_draft)
        if form.is_valid():
            gallery_error = validate_land_gallery_submission(
                request,
                existing_positions=land.images.values_list('position', flat=True),
            )
            if gallery_error:
                form.add_error(None, gallery_error)
            else:
                is_draft = request.POST.get('save_draft') == 'true'
                land = form.save(commit=False)
                land.is_draft = is_draft
                land.wizard_step = initial_step
                land.save()
                form.save_m2m()

                # Handle multiple images
                images = request.FILES.getlist('gallery_images')
                positions = request.POST.getlist('image_positions')
                
                for i, img in enumerate(images):
                    pos = positions[i]
                    LandImage.objects.create(
                        land=land,
                        image=img,
                        position=pos,
                        order=land.images.count() + i
                    )

                messages.success(request, 'Draft updated.' if is_draft else 'Land published successfully!')
                return redirect('lands:owner_dashboard')
    else:
        form = LandForm(instance=land)
    
    # If it's a draft, use the wizard (add_land.html)
    if land.is_draft:
        return render(request, 'lands/add_land.html', {
            'form': form, 
            'land': land, 
            'initial_step': initial_step
        })
    
    return render(request, 'lands/edit_land.html', {'form': form, 'land': land})


@owner_required
@require_http_methods(['GET', 'POST'])
def delete_land(request, pk):
    land = get_object_or_404(Land, pk=pk, owner=request.user)
    if request.method == 'POST':
        land.delete()
        messages.success(request, 'Land deleted.')
        return redirect('lands:owner_dashboard')
    return render(request, 'lands/delete_land.html', {'land': land})


# FIX #6: owner_required
@owner_required
def reservations_management(request):
    lands         = Land.objects.filter(owner=request.user)
    qs            = (Reservation.objects
                     .filter(land__in=lands)
                     .select_related('land', 'customer')
                     .order_by('-created_on'))
    pending_count = qs.filter(status='pending').count()
    awaiting_payment_count = qs.filter(status='awaiting_payment').count()
    sf = request.GET.get('status')
    if sf in ['pending', 'awaiting_payment', 'approved', 'rejected', 'cancelled']:
        qs = qs.filter(status=sf)
    from django.utils import timezone
    return render(request, 'lands/reservations_management.html', {
        'reservations': qs,
        'pending_count': pending_count,
        'awaiting_payment_count': awaiting_payment_count,
        'today': timezone.now().date(),
    })


@owner_required
def calendar_view(request):
    """Calendar view showing all bookings for owner's lands."""
    lands = Land.objects.filter(owner=request.user).prefetch_related('reservations')
    
    events = []
    for land in lands:
        for res in land.reservations.filter(status__in=['pending', 'awaiting_payment', 'approved']):
            if res.start_date and res.end_date:
                event = {
                    'id': res.id,
                    'title': f"{land.title} - {res.customer_name or res.customer.username}",
                    'start': res.start_date.isoformat(),
                    'end': (res.end_date + timedelta(days=1)).isoformat(),
                    'status': res.status,
                    'land_id': land.id,
                    'land_title': land.title,
                    'color': '#22c55e' if res.status == 'approved' else '#38bdf8' if res.status == 'awaiting_payment' else '#f59e0b',
                }
                events.append(event)
    
    return render(request, 'lands/calendar.html', {
        'lands': lands,
        'events_json': json.dumps(events),
    })


@login_required
@require_http_methods(['POST'])
def update_reservation_status(request, pk, status):
    r = get_object_or_404(Reservation, pk=pk)
    if r.land.owner != request.user:
        messages.error(request, 'Permission denied.')
        return redirect('lands:owner_dashboard')

    if status == 'approved':
        status = 'awaiting_payment'

    if status not in ['awaiting_payment', 'rejected', 'cancelled']:
        messages.error(request, 'Invalid status.')
        return redirect('lands:reservations_management')

    old_status = r.status

    # FIX #2: overlap check before approving rent bookings
    # BUG #3 FIX: Check both APPROVED and PENDING overlaps to prevent double-booking
    if status == 'awaiting_payment' and r.land.usage == 'rent':
        if r.start_date and r.end_date:
            conflict = Reservation.objects.filter(
                land=r.land, status__in=['approved', 'awaiting_payment', 'pending'],
                start_date__lt=r.end_date,
                end_date__gt=r.start_date
            ).exclude(pk=r.pk).exists()
            if conflict:
                messages.error(
                    request,
                    'Cannot approve this booking because another booking already covers those dates.',
                )
                return redirect('lands:reservations_management')

    r.status = status
    if status == 'awaiting_payment':
        pm = request.POST.get('payment_method', '').strip()
        pr = request.POST.get('payment_reference', '').strip()
        if pm: r.payment_method = pm
        if pr: r.payment_reference = pr
    r.save()

    # SMS on approval
    if status == 'awaiting_payment' and old_status != 'awaiting_payment':
        customer_phone = r.customer_phone
        if not customer_phone and r.customer:
            details = getattr(r.customer, 'personal_details', None)
            if details:
                customer_phone = details.phone
        
        if customer_phone:
            date_info = ''
            if r.start_date and r.end_date:
                date_info = f' ({r.start_date} to {r.end_date})'
            send_sms_notification(customer_phone,
                f"Your booking for '{r.land.title}'{date_info} is approved. "
                "Please complete payment in LandReserve to unlock access details.")
        
        # Create notification for customer
        customer = r.customer if r.customer else None
        if customer:
            create_notification(
                customer, 'booking_approved',
                'Booking Approved',
                f"Your booking for '{r.land.title}' has been approved. Tap Make payment to choose a payment method and complete your booking.",
                f"{reverse('lands:payments_and_bills')}?booking={r.id}"
            )

    # SMS on rejection
    if status == 'rejected' and old_status != 'rejected':
        customer_phone = r.customer_phone
        if not customer_phone and r.customer:
            details = getattr(r.customer, 'personal_details', None)
            if details:
                customer_phone = details.phone
        
        if customer_phone:
            send_sms_notification(customer_phone,
                f"Your booking request for '{r.land.title}' was not approved. "
                f"You may contact the owner or try another listing.")
        
        # Create notification for customer
        customer = r.customer if r.customer else None
        if customer:
            create_notification(
                customer, 'booking_rejected',
                'Booking Rejected',
                f"Your booking request for '{r.land.title}' was not approved.",
                f'/lands/reservations/'
            )

    messages.success(request, f'Reservation {status}.')
    next_url = request.META.get('HTTP_REFERER')
    return safe_redirect(request, next_url, 'lands:reservations_management')


@login_required
@require_http_methods(['POST'])
def mark_payment(request, pk):
    r = get_object_or_404(Reservation, pk=pk, land__owner=request.user)
    messages.info(
        request,
        'Payment verification is now handled by admin. Use the admin payments panel to confirm customer payments.'
    )
    return redirect('lands:reservations_management')


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN REPORTED LANDS DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@admin_required
def admin_reported_lands(request):
    """
    Admin dashboard to view all reported lands.
    Shows reports grouped by land and allows admin to review and take action.
    """
    # Get filter status
    status = request.GET.get('status', 'submitted')
    search = request.GET.get('search', '')
    
    # Get all reports, filter by status
    reports_qs = LandReport.objects.select_related('land', 'land__owner', 'reported_by').order_by('-created_on')
    
    if status != 'all':
        reports_qs = reports_qs.filter(status=status)
    
    if search:
        reports_qs = reports_qs.filter(
            Q(land__title__icontains=search) |
            Q(land__owner__username__icontains=search) |
            Q(reported_by__username__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Group reports by land
    lands_with_reports = {}
    for report in reports_qs:
        land_id = report.land.id
        if land_id not in lands_with_reports:
            lands_with_reports[land_id] = {
                'land': report.land,
                'reports': [],
                'total_reports': 0,
                'critical': False,
                'latest_status': 'submitted'
            }
        lands_with_reports[land_id]['reports'].append(report)
        lands_with_reports[land_id]['total_reports'] = len(lands_with_reports[land_id]['reports'])
        if report.status != 'dismissed':
            lands_with_reports[land_id]['latest_status'] = report.status
    
    # Pagination
    paginator = Paginator(list(lands_with_reports.values()), 15)
    page_number = request.GET.get('page', 1)
    lands_page = paginator.get_page(page_number)
    
    # Get stats
    total_reports = LandReport.objects.count()
    submitted_reports = LandReport.objects.filter(status='submitted').count()
    under_review = LandReport.objects.filter(status='reviewed').count()
    resolved = LandReport.objects.filter(status='resolved').count()
    
    context = {
        'lands_page': lands_page,
        'paginator': paginator,
        'status': status,
        'search': search,
        'total_reports': total_reports,
        'submitted_reports': submitted_reports,
        'under_review': under_review,
        'resolved': resolved,
        'status_choices': LandReport.STATUS_CHOICES,
    }
    
    return render(request, 'lands/admin_reported_lands.html', context)


@login_required
@admin_required
def admin_report_detail(request, report_id):
    """
    Admin view for detailed report inspection and action.
    """
    report = get_object_or_404(LandReport, pk=report_id)
    related_reports = LandReport.objects.filter(land=report.land).exclude(pk=report_id).order_by('-created_on')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        admin_notes = request.POST.get('admin_notes', '')
        new_status = request.POST.get('status', 'submitted')
        
        report.admin_notes = admin_notes
        report.status = new_status
        report.reviewed_by = request.user
        report.reviewed_on = timezone.now()
        
        if action == 'suspend_land':
            report.land.is_active = False
            report.land.save()
            messages.success(request, f'Land "{report.land.title}" has been suspended.')
        elif action == 'suspend_owner':
            report.land.owner.is_suspended = True
            report.land.owner.is_active = False
            report.land.owner.save()
            messages.success(request, f'Owner "{report.land.owner.username}" has been suspended.')
        elif action == 'dismiss':
            report.status = 'dismissed'
            messages.success(request, 'Report dismissed.')
        elif action == 'mark_spam':
            report.is_spam = True
            messages.success(request, 'Report marked as spam.')
        
        report.save()
        messages.success(request, 'Report action recorded.')
        return redirect('lands:admin_reported_lands')
    
    context = {
        'report': report,
        'related_reports': related_reports,
        'reason_choices': LandReport.REASON_CHOICES,
        'status_choices': LandReport.STATUS_CHOICES,
    }
    
    return render(request, 'lands/admin_report_detail.html', context)


@login_required
def report_listing(request, pk):
    """Allow authenticated users to flag a suspicious listing."""
    if request.method == 'POST':
        reason = sanitize_text(request.POST.get('reason', ''), 50)
        description = sanitize_text(request.POST.get('description', ''), 1000)
        land = get_object_or_404(Land, pk=pk)
        
        # Check if user already reported this land
        existing_report = LandReport.objects.filter(land=land, reported_by=request.user).first()
        if existing_report:
            messages.warning(request, 'You have already reported this listing. Our team will review it soon.')
        else:
            # Create report record
            LandReport.objects.create(
                land=land,
                reported_by=request.user,
                reason=reason,
                description=description,
            )
            messages.success(request, 'Report submitted. Our team will review this listing.')
            
            # Log for backup
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"LISTING REPORT: land_id={pk} '{land.title}' reported by "
                f"user={request.user.username} reason='{reason}'")
    return redirect('lands:land_detail', pk=pk)


# ── Messaging ─────────────────────────────────────────────────────────────────

@login_required
def inbox(request):
    received = Message.objects.filter(recipient=request.user).select_related('sender', 'land')
    sent = Message.objects.filter(sender=request.user).select_related('recipient', 'land')
    tab = request.GET.get('tab', 'inbox')
    unread_count = received.filter(is_read=False).count()
    return render(request, 'lands/inbox.html', {
        'received': received, 'sent': sent, 'tab': tab, 'unread_count': unread_count,
    })


@login_required
def contact_admin(request):
    """
    Finds the first active admin/operator user and redirects the user to the message thread with them.
    """
    admin = User.objects.filter(Q(is_staff=True) | Q(role='admin'), is_active=True).first()
    if not admin:
        admin = User.objects.filter(Q(is_staff=True) | Q(role='admin')).first()
        
    if not admin:
        messages.error(request, 'No administrator is currently available to receive messages.')
        return redirect('lands:inbox')
        
    return redirect('lands:message_thread', user_id=admin.id)


@login_required
def send_message(request):
    if request.method == 'POST':
        recipient_id = request.POST.get('recipient')
        land_id = request.POST.get('land')
        subject = sanitize_text(request.POST.get('subject', ''), 200)
        body = sanitize_text(request.POST.get('body', ''), 2000)
        if not body:
            messages.error(request, 'Message body cannot be empty.')
            return safe_redirect(request, request.META.get('HTTP_REFERER'), 'lands:inbox')
        recipient = get_object_or_404(User, pk=recipient_id)
        if recipient == request.user:
            messages.error(request, 'You cannot message yourself.')
            return safe_redirect(request, request.META.get('HTTP_REFERER'), 'lands:inbox')
        land = None
        if land_id:
            land = Land.objects.filter(pk=land_id).first()
        msg = Message.objects.create(
            sender=request.user, recipient=recipient,
            land=land, subject=subject, body=body
        )
        # Create a notification for the recipient
        is_admin_recipient = recipient.is_staff or recipient.role == 'admin'
        link = f"/admin-portal/owner-requests/{msg.id}/" if is_admin_recipient else f"/lands/messages/{request.user.id}/"
        create_notification(
            user=recipient,
            notification_type='message_received',
            title=f"New message from {request.user.get_full_name() or request.user.username}",
            message=body[:200],
            link=link
        )
        messages.success(request, f'Message sent to {recipient.username}.')
        return redirect('lands:inbox')
    return redirect('lands:inbox')


@login_required
def message_thread(request, user_id):
    other_user = get_object_or_404(User, pk=user_id)
    thread = Message.objects.filter(
        Q(sender=request.user, recipient=other_user) |
        Q(sender=other_user, recipient=request.user)
    ).select_related('sender', 'recipient', 'land').order_by('created_on')
    # Mark unread messages as read
    thread.filter(recipient=request.user, is_read=False).update(is_read=True)
    if request.method == 'POST':
        body = sanitize_text(request.POST.get('body', ''), 2000)
        land_id = request.POST.get('land')
        land = Land.objects.filter(pk=land_id).first() if land_id else None
        if body:
            msg = Message.objects.create(
                sender=request.user, recipient=other_user,
                land=land, body=body
            )
            # Create a notification for the recipient
            is_admin_recipient = other_user.is_staff or other_user.role == 'admin'
            link = f"/admin-portal/owner-requests/{msg.id}/" if is_admin_recipient else f"/lands/messages/{request.user.id}/"
            create_notification(
                user=other_user,
                notification_type='message_received',
                title=f"New message from {request.user.get_full_name() or request.user.username}",
                message=body[:200],
                link=link
            )
            messages.success(request, 'Reply sent.')
        return redirect('lands:message_thread', user_id=other_user.pk)
    return render(request, 'lands/message_thread.html', {
        'other_user': other_user, 'thread': thread,
    })


# ── Switch to Owner ───────────────────────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def toggle_wishlist(request, pk):
    land = get_object_or_404(Land, pk=pk)
    obj, created = Wishlist.objects.get_or_create(user=request.user, land=land)
    if not created:
        obj.delete()
        status = 'removed'
    else:
        status = 'added'
    
    # Handle AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
        return JsonResponse({'status': status, 'land_id': pk})
    
    # Handle regular requests
    if status == 'removed':
        messages.success(request, f'Removed "{land.title}" from your wishlist.')
    else:
        messages.success(request, f'Added "{land.title}" to your wishlist.')
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER', '')
    return safe_redirect(request, next_url, 'lands:land_detail', pk=pk)


@customer_required
@login_required
def my_wishlist(request):
    items = Wishlist.objects.filter(user=request.user).select_related('land', 'land__owner')
    return render(request, 'lands/wishlist.html', {'items': items})


@login_required
@require_http_methods(['POST'])
def switch_to_owner(request):
    user = request.user
    if user.role == User.ROLE_OWNER or user.is_owner:
        messages.info(request, 'You already have a Land Owner account.')
    else:
        user.role = User.ROLE_OWNER
        user.is_owner = True
        user.save()
        messages.success(request, 'Your account has been upgraded to Land Owner! You can now list lands.')
    request.session['current_mode'] = 'owner'
    return redirect('lands:owner_dashboard')


@login_required
@require_http_methods(['POST'])
def switch_mode(request):
    """Switch between customer and owner UI modes without logging out."""
    from django.http import JsonResponse
    user = request.user
    if user.is_staff or user.role == 'admin':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Admin cannot switch modes'}, status=403)
        messages.error(request, 'Admin accounts cannot switch modes.')
        return redirect('lands:land_list')

    is_owner_capable = user.role == 'owner' or user.is_owner
    if not is_owner_capable:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Upgrade to owner first'}, status=403)
        messages.info(request, 'You need to become a Land Owner first.')
        return redirect('lands:land_list')

    current = request.session.get('current_mode', 'customer')
    new_mode = 'owner' if current == 'customer' else 'customer'
    request.session['current_mode'] = new_mode

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'mode': new_mode,
            'redirect': '/lands/dashboard/' if new_mode == 'owner' else '/lands/dashboard/customer/',
        })

    if new_mode == 'owner':
        return redirect('lands:owner_dashboard')
    return redirect('lands:customer_dashboard')


# ── Help Center ───────────────────────────────────────────────────────────────

@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def help_center(request):
    """Help center with contact form for users to send support requests."""
    if request.method == 'POST':
        name = sanitize_text(request.POST.get('name', ''), 100)
        email = sanitize_text(request.POST.get('email', ''), 254)
        subject = sanitize_text(request.POST.get('subject', ''), 200)
        category = request.POST.get('category', 'general')
        message_body = sanitize_text(request.POST.get('message', ''), 2000)
        
        if not all([name, email, subject, message_body]):
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'lands/help_center.html')
        
        # Log the support request
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            f"SUPPORT REQUEST: from={name} <{email}> category={category} "
            f"subject='{subject}' message='{message_body[:100]}...'"
        )
        
        # Send email notification (if configured)
        support_email = getattr(settings, 'SUPPORT_EMAIL', 'support@landreserve.co.tz')
        try:
            from django.core.mail import send_mail
            send_mail(
                subject=f'[Land Reserve Support] {category.title()}: {subject}',
                message=f"From: {name} <{email}>\nCategory: {category}\n\n{message_body}",
                from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else email,
                recipient_list=[support_email],
                fail_silently=True,
            )
        except Exception as e:
            logger.warning(f"Failed to send support email: {e}")
        
        # Create database Message if authenticated
        if request.user.is_authenticated:
            admin = User.objects.filter(Q(is_staff=True) | Q(role='admin'), is_active=True).first()
            if not admin:
                admin = User.objects.filter(Q(is_staff=True) | Q(role='admin')).first()
            
            if admin:
                msg = Message.objects.create(
                    sender=request.user,
                    recipient=admin,
                    subject=f"[{category.upper()}] {subject}",
                    body=message_body
                )
                
                # Notify admin/operator
                create_notification(
                    user=admin,
                    notification_type='message_received',
                    title=f"New Support Request from {request.user.username}",
                    message=f"[{category.upper()}] {subject}",
                    link=f"/admin-portal/owner-requests/{msg.id}/"
                )
                
                messages.success(
                    request,
                    "Thank you for contacting us. We've received your message and will respond within 24 hours. You can follow and track this conversation in your Inbox.",
                )
                return redirect('lands:inbox')

        messages.success(
            request,
            "Thank you for contacting us. We've received your message and will respond within 24 hours.",
        )
        return redirect('lands:help_center')
    
    return render(request, 'lands/help_center.html')


# ── Notifications ───────────────────────────────────────────────────────────────

@login_required
def my_notifications(request):
    from lands.models import Notification
    base_qs = Notification.objects.filter(user=request.user).order_by('-created_on')
    unread_count = base_qs.filter(is_read=False).count()
    notifications = base_qs[:50]
    referer = request.META.get('HTTP_REFERER', '')
    if referer and not url_has_allowed_host_and_scheme(
        referer,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        referer = ''
    if not referer:
        if request.user.is_staff or request.user.role == User.ROLE_ADMIN:
            referer = reverse('accounts:admin_portal')
        elif request.user.role == User.ROLE_OWNER or request.user.is_owner:
            referer = reverse('lands:owner_dashboard')
        else:
            referer = reverse('lands:customer_dashboard')
    return render(request, 'lands/notifications.html', {
        'notifications': notifications,
        'unread_count': unread_count,
        'back_url': referer,
    })


@login_required
@require_http_methods(['POST'])
def mark_notification_read(request, notification_id):
    from lands.models import Notification
    notification = get_object_or_404(Notification, pk=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok'})
    return safe_redirect(request, request.META.get('HTTP_REFERER'), 'lands:my_notifications')


def live_search(request):
    """API for 'Search as you type' functionality."""
    query = request.GET.get('q', '').strip()
    mode = request.GET.get('mode', 'customer')  # 'customer' or 'owner'
    
    if len(query) < 2:
        return JsonResponse({'results': []})

    if mode == 'owner' and request.user.is_authenticated:
        # Search within owner's own lands
        lands = Land.objects.filter(owner=request.user)
        status = request.GET.get('status')
        usage = request.GET.get('usage')
        
        if status == 'published': lands = lands.filter(is_draft=False)
        elif status == 'draft': lands = lands.filter(is_draft=True)
        if usage in ['rent', 'sale']: lands = lands.filter(usage=usage)
        
        lands = lands.filter(Q(title__icontains=query) | Q(location__icontains=query))
    else:
        # Public search
        lands = Land.objects.filter(is_active=True, is_draft=False)
        usage = request.GET.get('type')
        max_price = request.GET.get('max_price')
        
        if usage in ['rent', 'sale']: lands = lands.filter(usage=usage)
        if max_price:
            try: lands = lands.filter(price__lte=float(max_price))
            except: pass
            
        lands = lands.filter(Q(title__icontains=query) | Q(location__icontains=query) | Q(description__icontains=query))

    results = []
    for land in lands.select_related('owner')[:6]:
        results.append({
            'id': land.id,
            'title': land.title,
            'location': land.location,
            'price': land.price_display,
            'image': land.primary_image.url if land.primary_image else None,
            'url': f"/lands/{land.id}/",
            'usage': land.get_usage_display(),
        })

    return JsonResponse({'results': results})
    

@login_required
@customer_required
def my_bookings(request):
    """View for customers to track their own land reservations."""
    bookings = Reservation.objects.filter(customer=request.user).select_related('land').order_by('-created_on')
    operator_payment_configs = OperatorPaymentConfig.objects.filter(is_active=True).order_by('priority')
    return render(request, 'lands/my_bookings.html', {'bookings': bookings, 'operator_payment_configs': operator_payment_configs})


@login_required
@customer_required
def payments_and_bills(request):
    bookings = (Reservation.objects
                .filter(customer=request.user)
                .select_related('land', 'land__owner')
                .prefetch_related('payments')
                .order_by('-created_on'))
    focus_booking_id = request.GET.get('booking')
    focus_booking = None
    if focus_booking_id:
        focus_booking = bookings.filter(pk=focus_booking_id).first()
    active_bookings = bookings.exclude(status__in=['rejected', 'cancelled'])
    outstanding_total = sum(
        booking.remaining_balance
        for booking in active_bookings
        if booking.remaining_balance > 0
    )
    operator_payment_configs = OperatorPaymentConfig.objects.filter(is_active=True).order_by('priority')
    return render(request, 'lands/payments_and_bills.html', {
        'bookings': bookings,
        'unpaid_count': sum(1 for booking in active_bookings if booking.payment_review_status == 'pending'),
        'under_review_count': sum(1 for booking in active_bookings if booking.payment_review_status == 'submitted'),
        'confirmed_count': sum(1 for booking in active_bookings if booking.payment_review_status == 'confirmed'),
        'outstanding_total': outstanding_total,
        'operator_payment_configs': operator_payment_configs,
        'focus_booking': focus_booking,
        'focus_booking_id': focus_booking_id,
    })


@login_required
@customer_required
def submit_payment(request, pk):
    """View for customers to submit payment proof (reference/receipt)."""
    booking = get_object_or_404(Reservation.objects.prefetch_related('payments'), pk=pk, customer=request.user)
    if booking.status != 'awaiting_payment':
        messages.error(request, 'You can submit payment only after the booking is awaiting payment.')
        return redirect('lands:payments_and_bills')
    if booking.remaining_balance <= 0:
        messages.info(request, 'This booking is already fully paid.')
        return redirect('lands:payments_and_bills')
    
    if request.method == 'POST':
        form = PaymentSubmissionForm(request.POST, request.FILES, reservation=booking)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.reservation = booking
            payment.created_by = request.user
            payment.updated_by = request.user
            payment.save()

            booking.payment_status = 'unpaid'
            booking.payment_confirmed = False
            booking.payment_reference = payment.payment_reference
            booking.payment_receipt = payment.payment_receipt
            booking.payment_date = payment.payment_date
            booking.payment_method = payment.payment_method
            booking.updated_by = request.user
            booking.save()
            
            notify_admins(
                notification_type='payment',
                title="Payment Submitted",
                message=(
                    f"Customer {request.user.username} submitted Tsh {payment.amount} for {booking.land.title}. "
                    f"Review reference: {payment.payment_reference}."
                ),
                link=reverse('accounts:admin_payment_detail', args=[payment.pk])
            )
            
            messages.success(request, "Payment details submitted successfully. An admin will review and confirm it.")
            return redirect('lands:payments_and_bills')
    else:
        form = PaymentSubmissionForm(reservation=booking, initial={'payment_method': booking.payment_method})
        
    return render(request, 'lands/submit_payment.html', {
        'form': form,
        'booking': booking,
        'payment_history': booking.payments.all()[:5],
    })


@login_required
@owner_required
def manage_payments(request):
    reservations = (Reservation.objects
                    .filter(land__owner=request.user)
                    .exclude(status__in=['rejected', 'cancelled'])
                    .select_related('land', 'customer')
                    .prefetch_related('payments')
                    .order_by('-created_on'))
    payment_filter = request.GET.get('payment', '')

    if payment_filter == 'awaiting':
        reservations = reservations.filter(Q(payment_reference__isnull=True) | Q(payment_reference=''))
    elif payment_filter == 'review':
        reservations = reservations.filter(payments__status='submitted').distinct()
    elif payment_filter == 'confirmed':
        reservations = reservations.filter(payments__status='confirmed').distinct()
    elif payment_filter == 'payout':
        reservations = reservations.filter(payments__status='confirmed', payments__owner_received_on__isnull=True).distinct()
    elif payment_filter == 'received':
        reservations = reservations.filter(payments__owner_received_on__isnull=False).distinct()

    owner_reservations = Reservation.objects.filter(land__owner=request.user).exclude(status__in=['rejected', 'cancelled'])
    confirmed_income = sum(booking.confirmed_amount_total for booking in owner_reservations.prefetch_related('payments'))
    platform_fee_total = sum(booking.platform_fee_total for booking in owner_reservations.prefetch_related('payments'))
    owner_net_total = sum(booking.owner_net_total for booking in owner_reservations.prefetch_related('payments'))
    expected_income = sum(
        (booking.total_amount or Decimal('0'))
        for booking in owner_reservations
        if booking.status in ['pending', 'awaiting_payment', 'approved']
    )

    return render(request, 'lands/manage_payments.html', {
        'reservations': reservations,
        'awaiting_count': owner_reservations.filter(Q(payment_reference__isnull=True) | Q(payment_reference='')).count(),
        'review_count': owner_reservations.filter(payments__status='submitted').distinct().count(),
        'confirmed_count': owner_reservations.filter(payments__status='confirmed').distinct().count(),
        'payout_pending_count': owner_reservations.filter(payments__status='confirmed', payments__owner_received_on__isnull=True).distinct().count(),
        'payout_received_count': owner_reservations.filter(payments__owner_received_on__isnull=False).distinct().count(),
        'confirmed_income': confirmed_income,
        'platform_fee_total': platform_fee_total,
        'owner_net_total': owner_net_total,
        'expected_income': expected_income,
    })


@login_required
@admin_required
def confirm_payment_receipt(request, pk):
    """Admin review action for customer-submitted payment proof."""
    booking = get_object_or_404(Reservation, pk=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        payment_id = request.POST.get('payment_id')
        payment = None
        if payment_id:
            payment = get_object_or_404(PaymentRecord, pk=payment_id, reservation=booking)

        if action == 'confirm':
            payment_method = request.POST.get('payment_method', '').strip()
            payment_reference = request.POST.get('payment_reference', '').strip()
            manual_amount = request.POST.get('amount', '').strip()
            if payment:
                if payment_method:
                    payment.payment_method = payment_method
                if payment_reference:
                    payment.payment_reference = payment_reference
                payment.status = 'confirmed'
                payment.updated_by = request.user
                payment.confirmed_on = timezone.now()
                payment = apply_platform_fee(payment)
                payment.save()
            else:
                try:
                    amount = Decimal(manual_amount)
                except Exception:
                    amount = None
                if amount is None or amount <= 0:
                    messages.error(request, 'Enter a valid payment amount before confirming.')
                    return redirect('lands:manage_payments')
                if amount > booking.remaining_balance:
                    messages.error(request, f'Amount cannot exceed remaining balance of Tsh {booking.remaining_balance}.')
                    return redirect('lands:manage_payments')
                payment = PaymentRecord(
                    reservation=booking,
                    amount=amount,
                    payment_method=payment_method or None,
                    payment_reference=payment_reference or f'MANUAL-{booking.id}-{timezone.now().strftime("%Y%m%d%H%M%S")}',
                    payment_date=booking.payment_date or timezone.now().date(),
                    notes='Recorded manually by admin.',
                    status='confirmed',
                    confirmed_on=timezone.now(),
                    created_by=request.user,
                    updated_by=request.user,
                )
                payment = apply_platform_fee(payment)
                payment.save()

            if payment_method:
                booking.payment_method = payment_method
            if payment_reference:
                booking.payment_reference = payment_reference
            elif payment:
                booking.payment_reference = payment.payment_reference
            if payment:
                booking.payment_receipt = payment.payment_receipt
                booking.payment_date = payment.payment_date
            booking.amount_paid = booking.confirmed_amount_total
            booking.payment_confirmed = booking.remaining_balance <= 0
            booking.payment_status = 'paid' if booking.remaining_balance <= 0 else 'unpaid'
            if booking.remaining_balance <= 0:
                booking.status = 'approved'
            elif booking.status == 'pending':
                booking.status = 'awaiting_payment'
            booking.updated_by = request.user
            booking.save()
            
            if booking.customer:
                create_notification(
                    user=booking.customer,
                    notification_type='payment',
                    title="Payment Confirmed",
                    message=f"Admin confirmed Tsh {payment.amount if payment else booking.amount_paid} for {booking.land.title}. Your booking is now updated and access details are unlocked when payment is complete.",
                    link=f"/lands/payments/"
                )
            if booking.land.owner:
                release_note = 'Funds will be released within 24 hours to 7 days.'
                if payment and payment.confirmed_on:
                    release_note = f"Funds are held until {payment.payout_release_due_on:%b %d, %Y}."
                create_notification(
                    user=booking.land.owner,
                    notification_type='payment',
                    title="Customer Payment Confirmed",
                    message=(
                        f"Admin confirmed Tsh {payment.amount if payment else booking.amount_paid} for {booking.land.title}. "
                        f"{release_note}"
                    ),
                    link="/lands/payments/manage/"
                )

            messages.success(request, f"Payment for booking #{booking.id} has been confirmed by admin.")
        
        elif action == 'reject':
            rejected_amount = None
            if payment:
                rejected_amount = payment.amount
                payment.status = 'rejected'
                payment.updated_by = request.user
                payment.save()

            latest_pending = booking.latest_pending_payment
            booking.payment_reference = latest_pending.payment_reference if latest_pending else ""
            booking.payment_receipt = latest_pending.payment_receipt if latest_pending else None
            booking.payment_date = latest_pending.payment_date if latest_pending else None
            booking.payment_method = latest_pending.payment_method if latest_pending else None
            booking.payment_confirmed = booking.remaining_balance <= 0
            booking.payment_status = 'paid' if booking.remaining_balance <= 0 else 'unpaid'
            booking.amount_paid = booking.confirmed_amount_total or None
            booking.save()
            
            if booking.customer:
                create_notification(
                    user=booking.customer,
                    notification_type='payment',
                    title="Payment Reference Rejected",
                    message=f"Admin could not verify your submitted payment of Tsh {rejected_amount or 0} for {booking.land.title}. Please check the details and resubmit.",
                    link=f"/lands/payments/"
                )
            messages.warning(request, "Payment reference rejected. Customer has been notified to resubmit.")

    return redirect('lands:manage_payments')


@login_required
@owner_required
@require_http_methods(['POST'])
def acknowledge_payout_received(request, payment_id):
    payment = get_object_or_404(
        PaymentRecord,
        pk=payment_id,
        reservation__land__owner=request.user,
    )

    if payment.status != 'confirmed':
        messages.error(request, 'Only admin-confirmed payments can be acknowledged.')
        return redirect('lands:manage_payments')

    if payment.owner_received_on:
        messages.info(request, 'This payout was already acknowledged.')
        return redirect('lands:manage_payments')

    payment.owner_received_on = timezone.now()
    payment.updated_by = request.user
    payment.save(update_fields=['owner_received_on', 'updated_by', 'updated_on'])

    if payment.reservation.customer:
        create_notification(
            user=payment.reservation.customer,
            notification_type='payment',
            title='Owner Acknowledged Payout',
            message=(
                f"The owner acknowledged receipt of the released payout for {payment.reservation.land.title}."
            ),
            link='/lands/payments/'
        )

    messages.success(request, 'Payout receipt acknowledged successfully.')
    return redirect('lands:manage_payments')
