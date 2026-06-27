#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'land_reservation.settings')
django.setup()

from lands.models import Land, LandImage

# Check demo lands
demo_lands = Land.objects.filter(title__contains='Demo')[:3]
for land in demo_lands:
    images = land.images.all()
    print(f"\n--- {land.title} ---")
    print(f"Basic: title={land.title}, usage={land.usage}, land_use={land.land_use}")
    print(f"Location: region={land.region}, district={land.district}, ward={land.ward}")
    print(f"Size: {land.size} {land.size_unit}")
    print(f"Price: {land.price} {land.price_unit}")
    print(f"Contact: {land.contact_phone}, {land.contact_email}")
    print(f"Images: {images.count()} total")
    for img in images[:3]:
        print(f"  - Position: {img.position}")
