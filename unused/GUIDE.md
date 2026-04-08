# LandReserve — Developer & Deployment Guide

---

## PART 1 — LOCAL DEVELOPMENT SETUP

### Step 1: Prerequisites

Make sure you have these installed:

```
Python 3.10 or newer      → python3 --version
pip                        → pip3 --version
Git                        → git --version
```

Install Python from https://python.org if needed.

---

### Step 2: Clone / Extract the Project

```bash
# If using Git:
git clone https://github.com/peter-web-art/land-reservation-system.git
cd land-reservation-system

# Or if you have the ZIP:
unzip fixed-land-reservation-system.zip
cd fixed-land-system
```

---

### Step 3: Create a Virtual Environment

```bash
# Create the environment
python3 -m venv venv

# Activate it (Linux / macOS):
source venv/bin/activate

# Activate it (Windows):
venv\Scripts\activate

# You should see (venv) at the start of your terminal prompt
```

---

### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs Django, Pillow (images), Twilio (SMS), django-axes (brute-force protection), django-ratelimit, bleach, whitenoise, gunicorn, django-cors-headers, and django-csp.

---

### Step 5: Run Database Migrations

```bash
python manage.py migrate
```

This creates all database tables (users, lands, reservations, axes lockout logs).

---

### Step 6: Create a Superuser (Admin Account)

```bash
python manage.py createsuperuser
```

Enter a username, email, and password when prompted. This account lets you log into /admin.

---

### Step 7: Start the Development Server

```bash
python manage.py runserver
```

Open your browser and go to:

```
http://127.0.0.1:8000         → Main site (browse lands)
http://127.0.0.1:8000/admin   → Django admin panel
http://127.0.0.1:8000/health  → System health check
```

The server auto-reloads when you save any Python or template file.

---

### Step 8: (Optional) Configure Twilio for SMS

In development you can skip this — bookings work without SMS. When you're ready to test SMS:

1. Create a free account at https://twilio.com
2. Get your Account SID, Auth Token, and a phone number
3. Set environment variables before running the server:

```bash
# Linux / macOS:
export TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
export TWILIO_AUTH_TOKEN=your_auth_token_here
export TWILIO_PHONE_NUMBER=+1234567890
python manage.py runserver

# Windows (Command Prompt):
set TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
set TWILIO_AUTH_TOKEN=your_auth_token_here
set TWILIO_PHONE_NUMBER=+1234567890
python manage.py runserver
```

---

## PART 2 — DEVELOPMENT TESTING

### Testing the Core User Flows

**A. Register and browse as a customer:**
1. Go to http://127.0.0.1:8000
2. Click Sign Up — create a customer account
3. Browse the land list and search using the hero search bar
4. Click a land listing → View Details → Reserve This Land
5. Fill in your phone number and confirm the booking
6. Go to My Bookings to see the pending reservation

**B. List a land as an owner:**
1. Log in (or register a second account)
2. Click My Lands → Add Land
3. Fill in title, location, price, description, upload an image
4. Go back to My Lands — your listing should appear
5. Click Manage Bookings to see reservations on your lands
6. Approve or Reject a reservation

**C. Anonymous booking (no account needed):**
1. Log out
2. Browse lands and click a listing
3. Book it — enter your name, email, and phone
4. Go to Check Booking and enter your email or phone to check status

**D. Admin panel:**
1. Go to http://127.0.0.1:8000/admin
2. Log in with your superuser credentials
3. You can view/edit all Users, Lands, Reservations, and Axes lockout logs

### Running Django's Built-in Checks

```bash
# Check for configuration issues:
python manage.py check

# Check for deployment readiness:
python manage.py check --deploy
```

### Collecting Static Files (test the production pipeline locally)

```bash
python manage.py collectstatic
```

---

## PART 3 — PRODUCTION DEPLOYMENT (Render.com — Free Tier)

Render is recommended: free tier, supports Python, auto-deploys from GitHub, free PostgreSQL.

### Step 1: Prepare Your Code for Production

**A. Push to GitHub:**

```bash
git init
git add .
git commit -m "Initial production-ready commit"
git remote add origin https://github.com/YOUR_USERNAME/land-reservation-system.git
git push -u origin main
```

**B. Make sure your `.gitignore` includes:**

```
venv/
__pycache__/
*.pyc
db.sqlite3
media/
staticfiles/
.env
```

---

### Step 2: Switch to PostgreSQL (Required for Production)

1. Add `psycopg2-binary` to requirements.txt:

```
psycopg2-binary>=2.9
```

2. Update `DATABASES` in `settings.py` to read from an environment variable:

```python
import dj_database_url   # pip install dj-database-url

DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=60
    )
}
```

Add `dj-database-url` to requirements.txt too.

---

### Step 3: Deploy on Render

1. Go to https://render.com and create a free account
2. Click **New → Web Service**
3. Connect your GitHub repository
4. Configure:
   - **Name:** land-reservation-system
   - **Environment:** Python
   - **Build Command:** `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
   - **Start Command:** `gunicorn land_reservation.wsgi:application`
5. Click **Advanced → Add Environment Variables** and add:

| Variable | Value |
|---|---|
| `SECRET_KEY` | (generate a random 50-char string) |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `your-app-name.onrender.com` |
| `DATABASE_URL` | (copy from your Render PostgreSQL dashboard) |
| `SECURE_SSL_REDIRECT` | `True` |
| `SESSION_COOKIE_SECURE` | `True` |
| `CSRF_COOKIE_SECURE` | `True` |
| `HSTS_SECONDS` | `31536000` |
| `CORS_ALLOWED_ORIGINS` | `https://your-app-name.onrender.com` |
| `TWILIO_ACCOUNT_SID` | (your Twilio SID) |
| `TWILIO_AUTH_TOKEN` | (your Twilio token) |
| `TWILIO_PHONE_NUMBER` | (your Twilio number) |

6. Also create a **PostgreSQL** database on Render (free tier), then copy its `DATABASE_URL` into the environment variables above.

7. Click **Create Web Service** — Render builds and deploys automatically.

---

### Step 4: Set Up Media File Storage (Cloudinary)

On Render's free tier, uploaded images are lost on redeploy. Use Cloudinary (free):

1. Sign up at https://cloudinary.com
2. Install: add `cloudinary` and `django-cloudinary-storage` to requirements.txt
3. In settings.py add:

```python
INSTALLED_APPS += ['cloudinary_storage', 'cloudinary']

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME'),
    'API_KEY':    os.environ.get('CLOUDINARY_API_KEY'),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET'),
}
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
```

4. Add `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` to Render's environment variables.

---

### Step 5: Generate a Strong SECRET_KEY

Run this in your terminal and use the output as your `SECRET_KEY` env var:

```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## PART 4 — PRODUCTION TESTING CHECKLIST

After deploying, verify each of these:

**Security:**
- [ ] `https://` works and HTTP redirects to HTTPS
- [ ] `/admin` is accessible only with superuser credentials
- [ ] Trying to access `/lands/add/` without login redirects to login page
- [ ] Submitting the login form 6 times with wrong password shows the lockout page
- [ ] Uploading a `.exe` or `.pdf` as a land image is rejected
- [ ] Going to `/health/` returns `{"status": "ok"}`

**Functionality:**
- [ ] Register a new account → lands dashboard appears
- [ ] Add a land listing with an image → image shows on the browse page
- [ ] Book a land as a different user → owner sees it in Manage Bookings
- [ ] Owner approves booking → SMS is sent (if Twilio configured)
- [ ] Anonymous check booking status works by email or phone
- [ ] Search by location, keyword, min/max price returns correct results
- [ ] Edit and delete land listings work correctly

**Performance:**
- [ ] All pages load under 3 seconds
- [ ] Images are served from Cloudinary (not the server)
- [ ] Static files (CSS/JS) are served by WhiteNoise with cache headers

---

## PART 5 — USEFUL MANAGEMENT COMMANDS

```bash
# Apply new migrations after model changes:
python manage.py makemigrations
python manage.py migrate

# Open Django shell for debugging:
python manage.py shell

# Reset all django-axes lockouts:
python manage.py axes_reset

# Check deployment security checklist:
python manage.py check --deploy

# Create a superuser on production:
python manage.py createsuperuser

# View all URL routes:
python manage.py show_urls   # needs django-extensions
```

---

## PART 6 — PROJECT STRUCTURE REFERENCE

```
land-reservation-system/
├── accounts/              # User registration, login, profile
│   ├── models.py          # Custom User model (phone, bio, profile_picture)
│   ├── views.py           # register, profile_edit
│   └── templates/
├── lands/                 # Core land & reservation app
│   ├── models.py          # Land, Reservation models
│   ├── views.py           # All views with rate limiting + sanitization
│   ├── urls.py            # URL routes
│   └── templates/
├── land_reservation/      # Django project config
│   ├── settings.py        # All settings (security, DB, static, etc.)
│   └── urls.py            # Root URL config + health check
├── templates/             # Global templates (base.html, 429.html)
├── requirements.txt       # All Python dependencies
├── .env.example           # Environment variable template
├── Procfile               # Gunicorn start command for Render/Heroku
└── GUIDE.md               # This file
```

---

## PART 7 — ADMIN PORTAL & USER MANAGEMENT

### Accessing the Admin Portal

There are two admin interfaces:

1. **LandReserve Admin Portal** at `/accounts/admin-portal/` — the friendly in-app portal for managing users, verifying owners, and suspending scammers.
2. **Django Admin** at `/admin/` — the full database management interface.

To access either, your account must have `is_staff = True` (set via Django admin) or `role = admin`.

### Making Yourself an Admin

After running the server for the first time:

```bash
# In the Django shell:
python manage.py shell
from accounts.models import User
u = User.objects.get(username='your_username')
u.is_staff = True
u.role = 'admin'
u.save()
exit()
```

Or use Django admin → Users → find your user → tick `Staff status`.

### Verifying a Land Owner (Anti-Scam)

1. Go to `/accounts/admin-portal/`
2. Find the owner in the "Owners Pending Verification" table
3. Click **✔ Verify** — they get a green "Verified" badge on all their listings
4. Unverified owners show an "Unverified" grey badge, warning customers to be cautious

### Suspending a Scammer

1. In the Admin Portal, find the user in "Recent Registrations"
2. Click **Suspend** — their account is deactivated immediately
3. They cannot log in even with the correct password
4. You can reinstate them later from the "Suspended Accounts" section

### User Roles

| Role | Description |
|---|---|
| Customer | Can browse, book, and check reservation status |
| Land Owner | Can also add/edit/delete land listings and manage bookings |
| Admin | Can access the admin portal and Django admin |

Users choose their role at registration and can change it in Profile Edit.

---

## PART 8 — BUN FRONTEND PIPELINE

This project uses [Bun](https://bun.sh) as its frontend package manager and build runner. Bun is a fast all-in-one JavaScript runtime that replaces npm/pnpm for frontend tasks.

### Install Bun

```bash
# Linux / macOS (one command):
curl -fsSL https://bun.sh/install | bash

# Windows (via Powershell):
powershell -c "irm bun.sh/install.ps1 | iex"

# Verify:
bun --version
```

### Install frontend dependencies

```bash
# From the fixed-land-system/ directory:
bun install
```

This installs Tailwind CSS, PostCSS, and Autoprefixer into `node_modules/` using Bun's ultra-fast installer.

### Build CSS

```bash
# One-time production build (outputs static/css/styles.css):
bun run build

# Watch mode during development (rebuilds on every file save):
bun run dev
```

### How it fits with Django

- **Development:** Tailwind CDN script in `base.html` handles styling automatically — no Bun needed.
- **Production:** Run `bun run build` before `collectstatic`. Remove the CDN `<script>` from `base.html` and rely on the compiled `static/css/styles.css` for better performance.

### Build pipeline files

| File | Purpose |
|---|---|
| `package.json` | Bun scripts + devDependency declarations |
| `tailwind.config.js` | Tailwind config (scans all Django templates) |
| `postcss.config.js` | PostCSS with Autoprefixer |
| `bunfig.toml` | Bun runtime settings |
| `static/css/src/main.css` | Source CSS input |
| `static/css/styles.css` | Compiled CSS output (served by Django) |

