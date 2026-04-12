# Land Reserve

Land Reserve is a Django-based land reservation and sales platform with customer browsing, owner listing management, KYC workflows, reservations, wishlists, messaging, and an admin review flow.

## Current Project Layout

```text
fixed-land-system/
|-- accounts/            Custom user model, KYC, auth flows
|-- docs/                Active project documents and reports
|-- lands/               Listings, reservations, wishlists, messaging
|-- land_reservation/    Django settings, URLs, context processors
|-- media/               Runtime uploads in local development
|-- static/              Active compiled CSS and shared static assets
|-- templates/           Shared templates and error pages
|-- .env.example         Environment variable template
|-- .gitignore
|-- manage.py
|-- README.md
|-- requirements.txt
```

Archived and unused material has been moved to:

`C:\Users\ECHO HEIGHTS AGENCY\Downloads\fixed-land-reservation-system\unused`

## Core Features

- Public land discovery with homepage search and detail pages
- Rent and buy listing flows
- Customer reservations, wishlist, and messaging
- Owner dashboards, listing management, and reservation management
- KYC submission and admin review
- Google OAuth support through Django Allauth
- Security hardening for redirects, CSRF handling, and rate limiting

## Tech Stack

- Python and Django
- SQLite by default
- Django templates, HTML, CSS, and JavaScript
- WhiteNoise for static file serving
- django-allauth, django-axes, django-csp, django-cors-headers

## Local Setup

1. Create and activate a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and adjust values as needed.
4. Run `python manage.py migrate`.
5. Optionally run `python manage.py createsuperuser`.
6. Start the app with `python manage.py runserver`.

## Important Environment Settings

Common variables:

```env
DEBUG=True
SECRET_KEY=change-me
ALLOWED_HOSTS=localhost,127.0.0.1
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=
```

If `DEBUG=False`, you must provide a real `SECRET_KEY`.

## Main Routes

- `/` landing page and listing discovery
- `/health/` application health check
- `/admin/` Django admin
- `/accounts/register/` modal-first registration entry
- `/accounts/login/` modal-first authentication entry
- `/accounts/profile/edit/` profile and KYC updates
- `/lands/` listing index
- `/lands/search/` filtered results
- `/lands/<id>/` listing detail
- `/lands/<id>/book/` reservation flow
- `/lands/dashboard/` owner dashboard
- `/lands/dashboard/customer/` customer dashboard
- `/lands/messages/` inbox
- `/lands/wishlist/` saved lands

## Documentation

See `docs/RESPONSIVE_DESIGN_GUIDE.md`, `docs/SYSTEM_ANALYSIS_AND_IMPROVEMENTS.md`, `docs/IMPLEMENTATION_REVIEW.md`, and `docs/CLEANUP_REPORT.md` for the current system notes.
