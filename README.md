# Land Reservation System

Land Reservation System is a Django application for land discovery, listing management, reservations, payment-proof tracking, messaging, notifications, and administrative oversight.

## Current Scope

- Public users can browse active land listings, search, and view listing details.
- Customers can register, manage profiles, reserve land, track bookings, submit payment proof, save wishlists, and message owners.
- Owners can create and manage listings, review reservations, confirm payments, and monitor listing activity.
- Administrators can review platform activity, manage users, approve or reject bookings, and change system settings.

## Project Structure

```text
land-reservation-system/
|-- accounts/            Custom user model, profile management, admin portal, auth flows
|-- docs/                Project documentation and schema references
|-- lands/               Listings, reservations, messaging, notifications, wishlist, search
|-- land_reservation/    Django settings, root URLs, shared context
|-- media/               Uploaded development media
|-- static/              CSS and shared static assets
|-- templates/           Shared templates and error pages
|-- .env.example         Environment variable template
|-- db.sqlite3           Local development database
|-- manage.py
|-- README.md
|-- requirements.txt
```

## Main Features

- Role-based accounts for customers, owners, and admins
- Public listing discovery with search, filters, live search, and location autocomplete
- Structured Tanzania location fields with region and district support
- Rent and sale listing support
- Partial-size reservation logic and availability checking
- Owner dashboards, reservation calendar, and reservation status updates
- Customer booking history and payment-proof submission
- In-app messaging and user notifications
- Wishlist saving and suspicious listing reporting
- Google OAuth support through `django-allauth`
- Password reset via Django auth
- Rate limiting, login lockouts, CSP, CORS, and upload restrictions

## Tech Stack

- Python 3
- Django 4.2
- SQLite by default
- Django templates, HTML, CSS, JavaScript
- WhiteNoise for static file serving
- `django-allauth`, `django-axes`, `django-csp`, `django-cors-headers`, `django-ratelimit`
- Twilio integration hooks for SMS notifications

## Local Setup

1. Create and activate a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and adjust values.
4. Run `python manage.py migrate`.
5. Optionally run `python manage.py createsuperuser`.
6. Start the server with `python manage.py runserver`.

## Important Environment Variables

```env
SECRET_KEY=replace-with-a-long-random-string
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
SUPPORT_EMAIL=support@landreserve.co.tz
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=
```

## Key Routes

- `/` public listing landing page
- `/health/` health check
- `/admin/` Django admin
- `/accounts/login/`
- `/accounts/register/`
- `/accounts/profile/edit/`
- `/accounts/admin-portal/`
- `/lands/`
- `/lands/search/`
- `/lands/api/live-search/`
- `/lands/<id>/`
- `/lands/<id>/book/`
- `/lands/dashboard/`
- `/lands/dashboard/customer/`
- `/lands/reservations/`
- `/lands/reservations/manage/`
- `/lands/reservations/calendar/`
- `/lands/messages/`
- `/lands/notifications/`
- `/lands/wishlist/`
- `/lands/my-bookings/`

## Documentation

- `docs/FUNCTIONAL_REQUIREMENTS.md`
- `docs/SYSTEM_ANALYSIS_AND_IMPROVEMENTS.md`
- `docs/IMPLEMENTATION_REVIEW.md`
- `docs/RESPONSIVE_DESIGN_GUIDE.md`
- `docs/database_schema_report.md`
- `docs/database_schema_notes.txt`
- `docs/database_schema.sql`
