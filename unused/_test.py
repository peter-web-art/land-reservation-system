import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'land_reservation.settings')
django.setup()
from django.test.client import Client
from accounts.models import User

# Create test users
owner, _ = User.objects.get_or_create(username='_testowner', defaults={
    'email': 'own@t.com', 'role': 'owner', 'is_owner': True
})
if _: owner.set_password('x'); owner.save()

admin_u, _ = User.objects.get_or_create(username='_testadmin', defaults={
    'email': 'admin@t.com', 'role': 'admin', 'is_staff': True
})
if _: admin_u.set_password('x'); admin_u.save()

cust, _ = User.objects.get_or_create(username='_testcust', defaults={
    'email': 'cust@t.com', 'role': 'customer'
})
if _: cust.set_password('x'); cust.save()

all_ok = True

# Anonymous pages
c = Client()
anon_pages = ['/', '/lands/', '/lands/search/', '/accounts/login/', '/accounts/register/']
print('=== ANONYMOUS ===')
for url in anon_pages:
    r = c.get(url)
    s = 'OK' if r.status_code == 200 else 'FAIL'
    if s == 'FAIL': all_ok = False
    print(f'  {s} {r.status_code} {url}')

# Customer pages
c = Client()
c.force_login(cust)
print('=== CUSTOMER ===')
cust_pages = [
    '/lands/dashboard/customer/', '/lands/reservations/',
    '/lands/messages/', '/lands/wishlist/'
]
for url in cust_pages:
    r = c.get(url)
    s = 'OK' if r.status_code in [200, 302] else 'FAIL'
    if s == 'FAIL': all_ok = False
    print(f'  {s} {r.status_code} {url}')

# Owner pages
c = Client()
c.force_login(owner)
print('=== OWNER ===')
owner_pages = [
    '/lands/dashboard/', '/lands/add/',
    '/lands/messages/', '/lands/reservations/manage/',
    '/accounts/profile/edit/'
]
for url in owner_pages:
    r = c.get(url)
    s = 'OK' if r.status_code in [200, 302] else 'FAIL'
    if s == 'FAIL': all_ok = False
    print(f'  {s} {r.status_code} {url}')

# Mode switching
print('=== MODE SWITCH ===')
r = c.post('/lands/switch-mode/')
loc = r.get('Location', '')
print(f'  Switch owner->customer: {r.status_code} -> {loc}')
r = c.post('/lands/switch-mode/')
loc = r.get('Location', '')
print(f'  Switch customer->owner: {r.status_code} -> {loc}')

# Admin pages
c = Client()
c.force_login(admin_u)
print('=== ADMIN ===')
r = c.get('/accounts/admin-portal/')
s = 'OK' if r.status_code == 200 else 'FAIL'
if s == 'FAIL': all_ok = False
print(f'  {s} {r.status_code} /accounts/admin-portal/')

# Test delete action
del_target, _ = User.objects.get_or_create(username='_delme', defaults={'email': 'del@t.com', 'role': 'customer'})
r = c.post(f'/accounts/admin-portal/{del_target.id}/action/', {'action': 'delete_user'})
deleted = not User.objects.filter(username='_delme').exists()
print(f'  Delete user: {"OK" if deleted else "FAIL"} (deleted={deleted})')
if not deleted: all_ok = False

# Template compilation check
print('=== TEMPLATE CHECK ===')
from django.template.loader import get_template
templates = [
    'base.html', '404.html', '500.html', 'registration/login.html',
    'lands/land_list.html', 'lands/land_detail.html', 'lands/search_results.html',
    'lands/customer_dashboard.html', 'lands/dashboard.html',
    'lands/inbox.html', 'lands/message_thread.html',
    'lands/add_land.html', 'lands/edit_land.html', 'lands/delete_land.html',
    'lands/book_land.html', 'lands/wishlist.html',
    'lands/my_reservations.html', 'lands/reservations_management.html',
    'accounts/profile_edit.html', 'accounts/admin_portal.html',
]
for t in templates:
    try:
        get_template(t)
        print(f'  OK {t}')
    except Exception as e:
        print(f'  FAIL {t}: {e}')
        all_ok = False

# Cleanup
User.objects.filter(username__startswith='_test').delete()
User.objects.filter(username='_delme').delete()
print(f'\n{"ALL OK" if all_ok else "SOME FAILURES"}')
