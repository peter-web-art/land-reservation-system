#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'land_reservation.settings')
django.setup()

from lands.models import Land
from accounts.models import User

# Get a demo owner
demo_owner = User.objects.filter(username__startswith='demo').first()
if demo_owner:
    lands = Land.objects.filter(owner=demo_owner)
    print(f'Demo owner: {demo_owner.username}')
    print(f'Lands owned: {lands.count()}')
    for land in lands[:3]:
        print(f'  - {land.title}: draft={land.is_draft}, active={land.is_active}, images={land.images.count()}')
else:
    print("No demo owner found. Available users:")
    users = User.objects.filter(username__contains='demo')
    for user in users[:5]:
        print(f"  - {user.username}")
