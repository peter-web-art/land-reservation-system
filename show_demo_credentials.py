#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'land_reservation.settings')
django.setup()

from accounts.models import User

print("=" * 70)
print("DEMO ACCOUNT CREDENTIALS")
print("=" * 70)

# Demo owners
print("\n📍 DEMO OWNERS (Land Listers):")
print("-" * 70)
owners = User.objects.filter(is_owner=True, username__startswith='demo_owner')
for owner in owners:
    print(f"\nUsername: {owner.username}")
    print(f"Email:    {owner.email}")
    print(f"Lands:    {owner.lands.count()}")
    print(f"Note:     Password = '{owner.username}'  (or use demo credentials)")

# Demo customers
print("\n\n👤 DEMO CUSTOMERS (Renters/Buyers):")
print("-" * 70)
customers = User.objects.filter(username__startswith='demo_', is_owner=False)[:10]
for customer in customers:
    print(f"\nUsername: {customer.username}")
    print(f"Email:    {customer.email}")
    print(f"Note:     Password = '{customer.username}'  (or use demo credentials)")

# Admin
print("\n\n🔐 DEMO ADMIN:")
print("-" * 70)
admin = User.objects.filter(is_staff=True, username='demo_admin').first()
if admin:
    print(f"Username: {admin.username}")
    print(f"Email:    {admin.email}")
    print(f"Note:     Password = 'demo_admin' (or use demo credentials)")

print("\n" + "=" * 70)
print("🔑 PASSWORD HINT:")
print("=" * 70)
print("Default password format: Use the username as password")
print("Example: demo_owner_alpha / demo_owner_alpha")
print("\nIf that doesn't work, reset password via Django shell or admin panel")
print("=" * 70)
