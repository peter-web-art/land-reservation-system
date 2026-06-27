import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'land_reservation.settings')
django.setup()

from lands.models import PaymentRecord

payments = PaymentRecord.objects.all()[:5]
for p in payments:
    print(f"Payment {p.payment_reference}: status={p.status}")
