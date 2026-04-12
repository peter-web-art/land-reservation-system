from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django import forms
from django.http import JsonResponse
from django.db.models import Q, F
from django.conf import settings
from django.utils.html import strip_tags
from django.utils.http import url_has_allowed_host_and_scheme
from django.core.paginator import Paginator
import bleach, re
from datetime import date as date_cls, timedelta

from .models import Land, Reservation, Message, Wishlist, LandImage
import json

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


# ── Helpers ───────────────────────────────────────────────────────────────────

def sanitize_text(value, max_length=None):
    if not value:
        return value
    cleaned = bleach.clean(value, tags=[], strip=True)
    cleaned = strip_tags(cleaned).strip()
    if max_length:
        cleaned = cleaned[:max_length]
    return cleaned


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


def owner_required(view_func):
    """Decorator: must be logged in AND have owner/admin role."""
    @login_required
    def _wrapped(request, *args, **kwargs):
        if request.user.role not in ('owner', 'admin') and not request.user.is_owner and not request.user.is_staff:
            messages.error(request, 'You need a Land Owner account to access this page.')
            return redirect('accounts:profile_edit')
        return view_func(request, *args, **kwargs)
    return _wrapped


# ── Forms ─────────────────────────────────────────────────────────────────────

class LandForm(forms.ModelForm):
    class Meta:
        model  = Land
        fields = ['title', 'description', 'price', 'price_unit', 'location',
                  'latitude', 'longitude',
                  'listing_type', 'size', 'size_unit', 'land_use',
                  'weekly_discount', 'monthly_discount',
                  'min_duration_days', 'max_duration_days',
                  'contact_phone', 'contact_email', 'image']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        owner = getattr(self.instance, 'owner', None)
        if owner:
            self.fields['contact_phone'].initial = getattr(owner, 'phone', '')
            self.fields['contact_email'].initial = getattr(owner, 'email', '')
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
        self.fields['price'].widget.attrs['placeholder']            = 'e.g. 150000'
        self.fields['weekly_discount'].widget.attrs['placeholder']  = 'e.g. 10  (means 10% off)'
        self.fields['monthly_discount'].widget.attrs['placeholder'] = 'e.g. 20  (means 20% off)'
        self.fields['min_duration_days'].widget.attrs['placeholder'] = 'e.g. 30'

    def clean_title(self):        return sanitize_text(self.cleaned_data.get('title'), 200)
    def clean_description(self):  return sanitize_text(self.cleaned_data.get('description'))
    def clean_location(self):     return sanitize_text(self.cleaned_data.get('location'), 200)

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image and hasattr(image, 'content_type'):
            if image.content_type not in ['image/jpeg', 'image/png', 'image/webp']:
                raise forms.ValidationError('Use JPG, PNG, or WebP only.')
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Max file size is 5 MB.')
        return image

    def clean(self):
        cleaned      = super().clean()
        listing_type = cleaned.get('listing_type')
        wd = cleaned.get('weekly_discount', 0) or 0
        md = cleaned.get('monthly_discount', 0) or 0
        if wd and not (0 <= wd <= 90):
            self.add_error('weekly_discount', 'Must be 0–90%.')
        if md and not (0 <= md <= 90):
            self.add_error('monthly_discount', 'Must be 0–90%.')
        if listing_type == 'sale':
            cleaned['price_unit']        = 'total'
            cleaned['weekly_discount']   = 0
            cleaned['monthly_discount']  = 0
            cleaned['min_duration_days'] = 1
            cleaned['max_duration_days'] = None
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
                  'start_date', 'end_date', 'payment_method', 'payment_reference', 'notes']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.land = kwargs.pop('land', None)
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
        self.fields['notes'].widget = forms.Textarea(attrs={
            'rows': 2, 'class': 'form-control',
            'placeholder': 'Any specific requirements, access instructions, or notes…'})
        self.fields['payment_reference'].widget.attrs['placeholder'] = 'e.g. M-Pesa: ABC123XY'
        today_str = date_cls.today().isoformat()
        self.fields['start_date'].widget.attrs['min'] = today_str
        self.fields['end_date'].widget.attrs['min']   = today_str
        if self.land and self.land.listing_type == 'sale':
            self.fields['start_date'].required = False
            self.fields['end_date'].required   = False
        elif self.land and self.land.listing_type == 'rent':
            self.fields['start_date'].required = True
            self.fields['end_date'].required   = True
        if self.user and self.user.is_authenticated:
            self.fields['customer_name'].initial  = self.user.get_full_name() or self.user.username
            self.fields['customer_email'].initial = self.user.email
            self.fields['customer_phone'].initial = getattr(self.user, 'phone', '')
            self.fields['customer_name'].widget   = forms.HiddenInput()
            self.fields['customer_email'].widget  = forms.HiddenInput()

    def clean_customer_phone(self):
        p = self.cleaned_data.get('customer_phone', '').strip()
        if p and not re.match(r'^[\d\+\s\-\(\)]{6,20}$', p):
            raise forms.ValidationError('Enter a valid phone number.')
        return p

    def clean(self):
        cleaned = super().clean()
        start   = cleaned.get('start_date')
        end     = cleaned.get('end_date')
        if self.land and self.land.listing_type == 'rent':
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
                    days = (end - start).days
                    if self.land.min_duration_days and days < self.land.min_duration_days:
                        self.add_error('start_date',
                            f'Minimum rental is {self.land.min_duration_days} days.')
                    if self.land.max_duration_days and days > self.land.max_duration_days:
                        self.add_error('end_date',
                            f'Maximum rental is {self.land.max_duration_days} days.')
                    # BUG FIX #9: check BOTH approved AND pending overlaps
                    if not self.land.is_available_for_dates(start, end):
                        self.add_error('start_date',
                            'This land is already booked or has a pending booking for those dates. '
                            'Please choose different dates.')
        return cleaned


# ── Views ─────────────────────────────────────────────────────────────────────

def land_list(request):
    lands = Land.objects.filter(is_active=True).select_related('owner').order_by('-created_at')
    
    # ── Filters from hero search bar & category tabs ──
    listing_type = request.GET.get('type')
    land_use     = request.GET.get('use')
    location     = request.GET.get('location')
    keyword      = request.GET.get('keyword', '')
    min_price    = request.GET.get('min_price')
    max_price    = request.GET.get('max_price')
    min_size     = request.GET.get('min_size')
    max_size     = request.GET.get('max_size')
    availability = request.GET.get('availability')
    
    if listing_type in ['rent', 'sale']:
        lands = lands.filter(listing_type=listing_type)
    if land_use in ['agricultural', 'residential', 'commercial', 'industrial', 'mixed']:
        lands = lands.filter(land_use=land_use)
    if location:
        lands = lands.filter(location__icontains=location)
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
        lands = lands.order_by('-created_at')

    # FIX #3: Build map_pins from queryset BEFORE converting to list via availability filter
    map_pins_qs = lands.filter(latitude__isnull=False, longitude__isnull=False)
    if availability == 'available':
        map_pins_qs = [l for l in map_pins_qs if l.is_available]
    elif availability == 'reserved':
        map_pins_qs = [l for l in map_pins_qs if not l.is_available]
    map_pins = json.dumps([
        {'id': l.id, 'title': l.title, 'lat': l.latitude, 'lng': l.longitude,
         'price': l.price_display, 'location': l.location, 'type': l.listing_type,
         'status': 'available' if l.is_available else 'reserved'}
        for l in map_pins_qs[:200]
    ])

    # Availability filter (may convert queryset → list — must happen after sort & map_pins)
    if availability == 'available':
        lands = [l for l in lands if l.is_available]
    elif availability == 'reserved':
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
    
    return render(request, 'lands/land_list.html', {
        'lands': page_obj, 'page_obj': page_obj, 'paginator': paginator,
        'map_pins': map_pins, 'wishlisted_ids': wishlisted_ids,
        'tanzania_regions': tanzania_regions,
        'current_filters': {
            'listing_type': listing_type,
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


@ratelimit(key='ip', rate='30/m', method='GET', block=True)
def search_lands(request):
    form  = SearchForm(request.GET)
    lands = Land.objects.filter(is_active=True).select_related('owner').order_by('-created_at')
    
    # Handle listing_type filter from navbar (rent/sale)
    listing_type = request.GET.get('listing_type')
    if listing_type in ['rent', 'sale']:
        lands = lands.filter(listing_type=listing_type)
    
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
        
        if loc: lands = lands.filter(location__icontains=loc)
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
        lands = lands.order_by('-created_at')

    # FIX #3: Build map_pins from queryset BEFORE converting to list
    map_pins_qs = lands.filter(latitude__isnull=False, longitude__isnull=False)
    if availability == 'available':
        map_pins_qs = [l for l in map_pins_qs if l.is_available]
    elif availability == 'reserved':
        map_pins_qs = [l for l in map_pins_qs if not l.is_available]
    map_pins = json.dumps([
        {'id': l.id, 'title': l.title, 'lat': l.latitude, 'lng': l.longitude,
         'price': l.price_display, 'location': l.location, 'type': l.listing_type,
         'status': 'available' if l.is_available else 'reserved'}
        for l in map_pins_qs[:200]
    ])

    # Availability filter (may convert QS → list — must happen after sort & map_pins)
    if availability == 'available':
        lands = [l for l in lands if l.is_available]
    elif availability == 'reserved':
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
    return render(request, 'lands/land_detail.html', {
        'land': land, 'similar_lands': similar, 'is_wishlisted': is_wishlisted,
    })


@ratelimit(key='ip', rate='10/m', method='POST', block=True)
def book_land(request, pk):
    land = get_object_or_404(Land, pk=pk, is_active=True)

    # FIX #1: prevent owner booking their own land
    if request.user.is_authenticated and request.user == land.owner:
        messages.warning(request, 'You cannot book your own listing.')
        return redirect('lands:land_detail', pk=land.pk)

    if land.listing_type == 'sale' and not land.is_available:
        messages.warning(request, 'This land has already been sold.')
        return redirect('lands:land_detail', pk=land.pk)

    initial   = {}
    qs_start  = request.GET.get('start')
    qs_end    = request.GET.get('end')
    if qs_start: initial['start_date'] = qs_start
    if qs_end:   initial['end_date']   = qs_end

    if request.method == 'POST':
        form = ReservationForm(request.POST, user=request.user, land=land)
        if form.is_valid():
            # FIX #1b: duplicate active booking check (rent + sale)
            if request.user.is_authenticated:
                existing = Reservation.objects.filter(
                    land=land, customer=request.user,
                    status__in=['pending', 'approved']).exists()
                if existing:
                    messages.warning(request,
                        'You already have an active or pending booking for this land.')
                    return redirect('lands:land_detail', pk=land.pk)
            r            = form.save(commit=False)
            r.land       = land
            r.status     = 'pending'
            r.start_date = form.cleaned_data.get('start_date')
            r.end_date   = form.cleaned_data.get('end_date')
            r.agreed_price = (land.calculate_price(r.start_date, r.end_date)
                              if r.start_date and r.end_date else land.price)
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

    return render(request, 'lands/book_land.html', {
        'land': land, 'form': form,
        'price_per_day': float(
            land.price / 30 if land.price_unit == 'month'
            else land.price / 365 if land.price_unit == 'year'
            else land.price),
        'weekly_discount':  float(land.weekly_discount),
        'monthly_discount': float(land.monthly_discount),
        'min_days': land.min_duration_days,
        'max_days': land.max_duration_days or 'null',
    })


@login_required
def my_reservations(request):
    reservations = (Reservation.objects
                    .filter(customer=request.user)
                    .select_related('land')
                    .order_by('-booking_date'))
    return render(request, 'lands/my_reservations.html', {'reservations': reservations})


@login_required
@require_http_methods(['POST'])
def cancel_reservation(request, pk):
    r = get_object_or_404(Reservation, pk=pk, customer=request.user)
    if r.status == 'pending':
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


@login_required
def customer_dashboard(request):
    qs        = Reservation.objects.filter(customer=request.user)
    total     = qs.count()
    pending   = qs.filter(status='pending').count()
    approved  = qs.filter(status='approved').count()
    cancelled = qs.filter(status='cancelled').count()
    recent    = qs.select_related('land').order_by('-booking_date')[:5]
    wishlist_count = Wishlist.objects.filter(user=request.user).count()
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('land', 'land__owner')[:4]
    return render(request, 'lands/customer_dashboard.html', {
        'total': total, 'pending': pending,
        'approved': approved, 'cancelled': cancelled,
        'recent_reservations': recent,
        'wishlist_count': wishlist_count, 'wishlist_items': wishlist_items,
    })


# FIX #5: owner_required instead of just login_required
@owner_required
def owner_dashboard(request):
    from django.db.models import Sum
    from django.utils import timezone
    from datetime import timedelta
    
    lands          = Land.objects.filter(owner=request.user).prefetch_related('reservations')
    ids            = lands.values_list('id', flat=True)
    pending_count  = Reservation.objects.filter(land_id__in=ids, status='pending').count()
    approved_count = Reservation.objects.filter(land_id__in=ids, status='approved').count()
    available_count = sum(1 for l in lands if l.is_available)
    recent_bookings = (Reservation.objects
                       .filter(land_id__in=ids)
                       .select_related('land', 'customer')
                       .order_by('-booking_date')[:8])
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
        booking_date__gte=thirty_days_ago,
    ).aggregate(total=Sum('amount_paid'))['total'] or 0
    
    # Last 7 days earnings
    weekly_earnings = Reservation.objects.filter(
        land_id__in=ids,
        status='approved',
        payment_status='paid',
        booking_date__gte=seven_days_ago
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
    })


# FIX #4: owner_required
@owner_required
@ratelimit(key='user', rate='20/m', method='POST', block=True)
def add_land(request):
    if request.method == 'POST':
        form = LandForm(request.POST, request.FILES)
        if form.is_valid():
            land       = form.save(commit=False)
            land.owner = request.user
            land.save()
            
            # Handle gallery images
            gallery_files = request.FILES.getlist('gallery_images')
            for i, image_file in enumerate(gallery_files):
                LandImage.objects.create(
                    land=land,
                    image=image_file,
                    is_primary=(i == 0 and not land.image),
                    order=i
                )

            messages.success(request, f'"{land.title}" listed successfully.')
            return redirect('lands:owner_dashboard')
    else:
        form = LandForm()
    return render(request, 'lands/add_land.html', {'form': form})


# FIX #4: owner_required
@owner_required
@ratelimit(key='user', rate='20/m', method='POST', block=True)
def edit_land(request, pk):
    land = get_object_or_404(Land, pk=pk, owner=request.user)
    if request.method == 'POST':
        form = LandForm(request.POST, request.FILES, instance=land)
        if form.is_valid():
            form.save()
            messages.success(request, 'Listing updated.')
            return redirect('lands:owner_dashboard')
    else:
        form = LandForm(instance=land)
    return render(request, 'lands/edit_land.html', {'form': form, 'land': land})


@login_required
@require_http_methods(['GET', 'POST'])
def delete_land(request, pk):
    land = get_object_or_404(Land, pk=pk, owner=request.user)
    if request.method == 'POST':
        land.delete()
        messages.success(request, 'Listing deleted.')
        return redirect('lands:owner_dashboard')
    return render(request, 'lands/delete_land.html', {'land': land})


# FIX #6: owner_required
@owner_required
def reservations_management(request):
    lands         = Land.objects.filter(owner=request.user)
    qs            = (Reservation.objects
                     .filter(land__in=lands)
                     .select_related('land', 'customer')
                     .order_by('-booking_date'))
    pending_count = qs.filter(status='pending').count()
    sf = request.GET.get('status')
    if sf in ['pending', 'approved', 'rejected', 'cancelled']:
        qs = qs.filter(status=sf)
    return render(request, 'lands/reservations_management.html', {
        'reservations': qs,
        'pending_count': pending_count,
    })


@owner_required
def calendar_view(request):
    """Calendar view showing all bookings for owner's lands."""
    lands = Land.objects.filter(owner=request.user).prefetch_related('reservations')
    
    events = []
    for land in lands:
        for res in land.reservations.filter(status__in=['pending', 'approved']):
            if res.start_date and res.end_date:
                event = {
                    'id': res.id,
                    'title': f"{land.title} - {res.customer_name or res.customer.username}",
                    'start': res.start_date.isoformat(),
                    'end': (res.end_date + timedelta(days=1)).isoformat(),
                    'status': res.status,
                    'land_id': land.id,
                    'land_title': land.title,
                    'color': '#22c55e' if res.status == 'approved' else '#f59e0b',
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

    if status not in ['approved', 'rejected', 'cancelled']:
        messages.error(request, 'Invalid status.')
        return redirect('lands:reservations_management')

    old_status = r.status

    # FIX #2: overlap check before approving rent bookings
    if status == 'approved' and r.land.listing_type == 'rent':
        if r.start_date and r.end_date:
            conflict = Reservation.objects.filter(
                land=r.land, status='approved',
                start_date__lt=r.end_date,
                end_date__gt=r.start_date
            ).exclude(pk=r.pk).exists()
            if conflict:
                messages.error(
                    request,
                    'Cannot approve this booking because another approved booking already covers those dates.',
                )
                return redirect('lands:reservations_management')

    r.status = status
    if status == 'approved':
        pm = request.POST.get('payment_method', '').strip()
        pr = request.POST.get('payment_reference', '').strip()
        if pm: r.payment_method = pm
        if pr:
            r.payment_reference = pr
            r.payment_status    = 'paid'
            r.amount_paid       = r.agreed_price or r.land.price  # FIX #3
    r.save()

    # SMS on approval
    if status == 'approved' and old_status != 'approved':
        phone = r.customer_phone or (r.customer.phone if r.customer else None)
        if phone:
            date_info = ''
            if r.start_date and r.end_date:
                date_info = f' ({r.start_date} to {r.end_date})'
            send_sms_notification(phone,
                f"Your booking for '{r.land.title}'{date_info} is approved. "
                f"Contact owner: {r.land.contact_phone or 'see listing'}.")
        
        # Create notification for customer
        customer = r.customer if r.customer else None
        if customer:
            create_notification(
                customer, 'booking_approved',
                'Booking Approved',
                f"Your booking for '{r.land.title}' has been approved!",
                f'/lands/reservations/'
            )

    # SMS on rejection
    if status == 'rejected' and old_status != 'rejected':
        phone = r.customer_phone or (r.customer.phone if r.customer else None)
        if phone:
            send_sms_notification(phone,
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
    return redirect('lands:reservations_management')


@login_required
@require_http_methods(['POST'])
def mark_payment(request, pk):
    r = get_object_or_404(Reservation, pk=pk)
    if r.land.owner != request.user:
        messages.error(request, 'Permission denied.')
        return redirect('lands:reservations_management')
    r.payment_status    = 'paid'
    r.payment_method    = request.POST.get('payment_method', r.payment_method)
    r.payment_reference = request.POST.get('payment_reference', r.payment_reference or '')
    r.amount_paid       = r.agreed_price or r.land.price   # FIX #3: use agreed_price
    r.save()
    messages.success(request, 'Payment recorded.')
    return redirect('lands:reservations_management')


def report_listing(request, pk):
    """Allow anyone to flag a suspicious listing."""
    if request.method == 'POST' and request.user.is_authenticated:
        reason = sanitize_text(request.POST.get('reason', ''), 500)
        land   = get_object_or_404(Land, pk=pk)
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            f"LISTING REPORT: land_id={pk} '{land.title}' reported by "
            f"user={request.user.username} reason='{reason}'")
        messages.success(request, 'Report submitted. Our team will review this listing.')
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
        Message.objects.create(
            sender=request.user, recipient=recipient,
            land=land, subject=subject, body=body
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
    ).select_related('sender', 'recipient', 'land').order_by('created_at')
    # Mark unread messages as read
    thread.filter(recipient=request.user, is_read=False).update(is_read=True)
    if request.method == 'POST':
        body = sanitize_text(request.POST.get('body', ''), 2000)
        land_id = request.POST.get('land')
        land = Land.objects.filter(pk=land_id).first() if land_id else None
        if body:
            Message.objects.create(
                sender=request.user, recipient=other_user,
                land=land, body=body
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
    notifications = Notification.objects.filter(user=request.user)[:50]
    unread_count = notifications.filter(is_read=False).count()
    return render(request, 'lands/notifications.html', {
        'notifications': notifications,
        'unread_count': unread_count,
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
