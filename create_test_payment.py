import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'land_reservation.settings')
django.setup()

from lands.models import PaymentRecord, Reservation
from django.utils import timezone

# Get a reservation to attach payment to
reservation = Reservation.objects.first()

if reservation:
    # Create a test payment with 'submitted' status
    payment = PaymentRecord.objects.create(
        reservation=reservation,
        amount=100000,
        payment_method='mpesa',
        payment_reference='TEST_SUBMITTED_001',
        payment_date=timezone.now().date(),
        notes='Test payment to verify confirm button',
        status='submitted'  # Key: this makes it show the confirm/reject buttons
    )
    print(f"✓ Created test payment: {payment.payment_reference} with status='{payment.status}'")
    print(f"  Payment ID: {payment.pk}")
    print(f"  Reservation: {reservation}")
else:
    print("No reservations found to attach payment to")
