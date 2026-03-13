from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django import forms
from django.db.models import Q
from .models import Land, Reservation
from accounts.models import User
from twilio.rest import Client
from django.conf import settings

def send_sms_notification(phone_number, message):
    """Send SMS notification using Twilio"""
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        return True
    except Exception as e:
        # Log the error, but don't fail the approval
        print(f"SMS sending failed: {e}")
        return False

# Form for adding land
class LandForm(forms.ModelForm):
    class Meta:
        model = Land
        fields = ['title', 'description', 'price', 'location', 'listing_type', 'contact_phone', 'contact_email', 'image']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-fill contact info from user (owner field may not exist yet)
        owner = getattr(self.instance, 'owner', None)
        if owner is not None:
            # use attributes safely, handle missing fields
            self.fields['contact_phone'].initial = getattr(owner, 'phone', '')
            self.fields['contact_email'].initial = getattr(owner, 'email', '')


# Form for searching lands
class SearchForm(forms.Form):
    location = forms.CharField(max_length=200, required=False, label='Location')
    min_price = forms.DecimalField(required=False, label='Min Price', decimal_places=2)
    max_price = forms.DecimalField(required=False, label='Max Price', decimal_places=2)
    keyword = forms.CharField(max_length=200, required=False, label='Keyword (Title/Description)')

# Form for reservations
class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['customer_name', 'customer_email', 'customer_phone']
        
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # If user is logged in, pre-fill their info
        if self.user and self.user.is_authenticated:
            self.fields['customer_name'].initial = self.user.get_full_name() or self.user.username
            self.fields['customer_email'].initial = self.user.email
            # Hide fields that are already known
            self.fields['customer_name'].widget = forms.HiddenInput()
            self.fields['customer_email'].widget = forms.HiddenInput()

# Owner dashboard – list lands
@login_required
def owner_dashboard(request):
    lands = Land.objects.filter(owner=request.user)
    return render(request, 'lands/dashboard.html', {'lands': lands})

# Add land
@login_required
def add_land(request):
    if request.method == 'POST':
        form = LandForm(request.POST, request.FILES)
        if form.is_valid():
            land = form.save(commit=False)
            land.owner = request.user
            land.save()
            return redirect('lands:owner_dashboard')
    else:
        form = LandForm()
    return render(request, 'lands/add_land.html', {'form': form})

# Edit existing land
@login_required
def edit_land(request, pk):
    land = Land.objects.get(pk=pk, owner=request.user)
    if request.method == 'POST':
        form = LandForm(request.POST, request.FILES, instance=land)
        if form.is_valid():
            land = form.save(commit=False)
            land.owner = request.user
            land.save()
            return redirect('lands:owner_dashboard')
    else:
        form = LandForm(instance=land)
    return render(request, 'lands/edit_land.html', {'form': form, 'land': land})

# Delete land
@login_required
def delete_land(request, pk):
    land = Land.objects.get(pk=pk, owner=request.user)
    if request.method == 'POST':
        land.delete()
        return redirect('lands:owner_dashboard')
    # confirmation page
    return render(request, 'lands/delete_land.html', {'land': land})

def land_list(request):
    lands = Land.objects.all()
    return render(request, 'lands/land_list.html', {'lands': lands})

# Search lands
def search_lands(request):
    form = SearchForm(request.GET)
    lands = Land.objects.all()
    
    if form.is_valid():
        location = form.cleaned_data.get('location')
        min_price = form.cleaned_data.get('min_price')
        max_price = form.cleaned_data.get('max_price')
        keyword = form.cleaned_data.get('keyword')
        
        if location:
            lands = lands.filter(location__icontains=location)
        
        if min_price:
            lands = lands.filter(price__gte=min_price)
        
        if max_price:
            lands = lands.filter(price__lte=max_price)
        
        if keyword:
            lands = lands.filter(
                Q(title__icontains=keyword) | Q(description__icontains=keyword)
            )
    
    return render(request, 'lands/search_results.html', {'lands': lands, 'form': form})

# Add land detail view
def land_detail(request, pk):
    land = Land.objects.get(pk=pk)
    return render(request, 'lands/land_detail.html', {'land': land})

# Book a land
def book_land(request, pk):
    land = Land.objects.get(pk=pk)
    
    if not land.is_available:
        return redirect('lands:land_detail', pk=land.pk)
    
    if request.method == 'POST':
        form = ReservationForm(request.POST, user=request.user)
        if form.is_valid():
            # Check if already reserved (only for logged-in users)
            if request.user.is_authenticated:
                existing = Reservation.objects.filter(land=land, customer=request.user, status__in=['pending', 'approved']).exists()
                if existing:
                    return redirect('lands:land_detail', pk=land.pk)
            
            reservation = form.save(commit=False)
            reservation.land = land
            if request.user.is_authenticated:
                reservation.customer = request.user
            reservation.status = 'pending'
            reservation.save()
            return redirect('lands:my_reservations') if request.user.is_authenticated else redirect('lands:land_list')
    else:
        form = ReservationForm(user=request.user)
    
    return render(request, 'lands/book_land.html', {'land': land, 'form': form})

# Check booking status (for anonymous users)
def check_booking_status(request):
    reservations = None
    if request.method == 'POST':
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        if email or phone:
            filters = Q()
            if email:
                filters |= Q(customer_email=email) | Q(customer__email=email)
            if phone:
                filters |= Q(customer_phone=phone) | Q(customer__phone=phone)
            reservations = Reservation.objects.filter(filters).select_related('land')
    
    return render(request, 'lands/check_status.html', {'reservations': reservations})

# View user's reservations
@login_required
def my_reservations(request):
    reservations = Reservation.objects.filter(customer=request.user).select_related('land')
    return render(request, 'lands/my_reservations.html', {'reservations': reservations})

# Cancel a reservation (customer)
@login_required
def cancel_reservation(request, pk):
    try:
        reservation = Reservation.objects.get(pk=pk, customer=request.user)
    except Reservation.DoesNotExist:
        return redirect('lands:my_reservations')
    # only allow cancelling pending or approved
    if reservation.status in ['pending', 'approved']:
        reservation.status = 'cancelled'
        reservation.save()
    return redirect('lands:my_reservations')

# Customer dashboard (basic overview)
@login_required
def customer_dashboard(request):
    total = Reservation.objects.filter(customer=request.user).count()
    pending = Reservation.objects.filter(customer=request.user, status='pending').count()
    approved = Reservation.objects.filter(customer=request.user, status='approved').count()
    cancelled = Reservation.objects.filter(customer=request.user, status='cancelled').count()
    return render(request, 'lands/customer_dashboard.html', {
        'total': total,
        'pending': pending,
        'approved': approved,
        'cancelled': cancelled,
    })

# View reservations for owner's lands
@login_required
def reservations_management(request):
    lands = Land.objects.filter(owner=request.user)
    reservations = Reservation.objects.filter(land__in=lands).select_related('land', 'customer')
    return render(request, 'lands/reservations_management.html', {'reservations': reservations})

# Update reservation status
@login_required
def update_reservation_status(request, pk, status):
    reservation = Reservation.objects.get(pk=pk)
    
    # Verify user is the owner of the land
    if reservation.land.owner != request.user:
        return redirect('lands:owner_dashboard')
    
    if status in ['approved', 'rejected', 'cancelled']:
        old_status = reservation.status
        reservation.status = status
        reservation.save()
        
        # Send SMS notification if approved
        if status == 'approved' and old_status != 'approved':
            phone_number = reservation.customer_phone or (reservation.customer.phone if reservation.customer else None)
            if phone_number:
                message = f"Your booking for {reservation.land.title} has been approved! Contact: {reservation.land.contact_phone or 'N/A'}"
                send_sms_notification(phone_number, message)
    
    return redirect('lands:reservations_management')

