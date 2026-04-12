"""
Django settings for land_reservation project.
Security-hardened configuration.
"""
import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# ─── SECRET KEY ──────────────────────────────────────────────────────────────
# In production, set the SECRET_KEY environment variable to a strong random value.
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-xd$)0%cnv(@zv0=i#$e6s3x08w-0*$vdjwl=yqww+v&*ori&+f'
)

# ─── DEBUG / HOSTS ───────────────────────────────────────────────────────────
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

if not DEBUG and SECRET_KEY.startswith('django-insecure-'):
    raise ImproperlyConfigured('Set a unique SECRET_KEY in the environment when DEBUG is False.')

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver').split(',')

# ─── AUTH REDIRECTS ──────────────────────────────────────────────────────────
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
LOGIN_URL = '/accounts/login/'

# ─── INSTALLED APPS ──────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    # Third-party security
    'axes',               # Brute-force login protection
    'corsheaders',        # CORS configuration
    'csp',                # Content Security Policy
    # Allauth (Google OAuth)
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    # Project apps
    'accounts',
    'lands',
]

SITE_ID = 1

# ─── MIDDLEWARE ───────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    # CORS must be as high as possible
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # CSRF protection (built-in SQL injection prevention via ORM)
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # Brute-force protection (axes)
    'axes.middleware.AxesMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Clickjacking / XFrameOptions
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Content Security Policy
    'csp.middleware.CSPMiddleware',
    # Allauth
    'allauth.account.middleware.AccountMiddleware',
]

# ─── AUTHENTICATION BACKENDS ─────────────────────────────────────────────────
AUTHENTICATION_BACKENDS = [
    # axes must be first
    'axes.backends.AxesStandaloneBackend',
    'accounts.backends.SuspendedAwareBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

ROOT_URLCONF = 'land_reservation.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.template.context_processors.media',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'land_reservation.context_processors.global_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'land_reservation.wsgi.application'

# ─── DATABASE ────────────────────────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        # Connection pooling (persistent connections — 60s timeout)
        'CONN_MAX_AGE': 60,
    }
}

AUTH_USER_MODEL = 'accounts.User'

# ─── PASSWORD VALIDATION ─────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ─── INTERNATIONALISATION ────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Dar_es_Salaam'
USE_I18N = True
USE_TZ = True

# ─── STATIC & MEDIA FILES ────────────────────────────────────────────────────
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG else
            "whitenoise.storage.CompressedManifestStaticFilesStorage"
        ),
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── EMAIL BACKEND ────────────────────────────────────────────────────────────
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@landreserve.co.tz')

# Support email for receiving help center submissions
SUPPORT_EMAIL = os.environ.get('SUPPORT_EMAIL', 'support@landreserve.co.tz')

# Site configuration
SITE_NAME = os.environ.get('SITE_NAME', 'LandReserve')

# ══════════════════════════════════════════════════════════════════════════════════
#  SECURITY SETTINGS
# ═════════════════════════════════════════════════════════════════════════════════

# ── 1. Security Headers (equivalent to Helmet.js) ────────────
SECURE_BROWSER_XSS_FILTER = True           # X-XSS-Protection header
SECURE_CONTENT_TYPE_NOSNIFF = True         # X-Content-Type-Options: nosniff
X_FRAME_OPTIONS = 'DENY'                   # Clickjacking protection
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# HTTPS-only settings (enable when behind SSL in production)
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'False') == 'True'
SECURE_HSTS_SECONDS = int(os.environ.get('HSTS_SECONDS', '0'))  # Set to 31536000 in prod
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False') == 'True'
CSRF_COOKIE_SECURE = os.environ.get('CSRF_COOKIE_SECURE', 'False') == 'True'

# ── 2. Session Security ───────────────────────────────────────────────────────
SESSION_COOKIE_HTTPONLY = True    # JS cannot read session cookie
SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF via cross-site navigation blocked
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7  # 1 week

CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# ── 3. Content Security Policy (XSS Protection) — django-csp 4.0 format ────
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ("'self'",),
        "script-src": (
            "'self'",
            "'unsafe-inline'",               # Required for onclick handlers + inline <script> blocks
            "https://cdn.jsdelivr.net",       # Bootstrap JS
            "https://unpkg.com",              # Leaflet.js + plugins
            "https://cdnjs.cloudflare.com",   # Leaflet plugins CDN
        ),
        "style-src": (
            "'self'",
            "'unsafe-inline'",                # Bootstrap inline styles
            "https://cdn.jsdelivr.net",
            "https://fonts.googleapis.com",
            "https://unpkg.com",              # Leaflet.css
            "https://cdnjs.cloudflare.com",   # Leaflet plugin styles
        ),
        "font-src": (
            "'self'",
            "https://cdn.jsdelivr.net",
            "https://fonts.gstatic.com",
        ),
        "img-src": (
            "'self'",
            "data:",
            "blob:",
            "https://images.unsplash.com",    # Hero background
            "https://res.cloudinary.com",     # Cloudinary uploads (production)
            "https://*.tile.openstreetmap.org", # Leaflet map tiles
            "https://*.arcgisonline.com",     # Esri satellite tiles
        ),
        "connect-src": (
            "'self'",
            "https://api.open-meteo.com",     # Live weather API
            "https://accounts.google.com",    # Google OAuth
        ),
        "frame-ancestors": ("'none'",),       # No iframing (complements X-Frame-Options)
        "worker-src": ("'self'", "blob:"),   # Required for marker clustering
    }
}

# ── 4. CORS Configuration ─────────────────────────────────────────────────────
# Only allow same-origin requests (tighten CORS_ALLOWED_ORIGINS in production)
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = os.environ.get(
    'CORS_ALLOWED_ORIGINS', 'http://localhost:8000'
).split(',')
CORS_ALLOW_CREDENTIALS = False

# ── 5. Rate Limiting (django-ratelimit) ───────────────────────────────────────
# Applied per-view via @ratelimit decorator in views.py
# Default: 30 requests / minute per IP
RATELIMIT_USE_CACHE = 'default'
RATELIMIT_FAIL_OPEN = False  # Block on cache failure — safer default

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'land-reservation-cache',
    }
}

# ── 6. Brute-Force Login Protection (django-axes) ─────────────────────────────
AXES_FAILURE_LIMIT = 5           # Lock after 5 failed attempts
AXES_COOLOFF_TIME = 1            # Lockout duration in hours
AXES_LOCKOUT_TEMPLATE = 'accounts/lockout.html'
AXES_RESET_ON_SUCCESS = True     # Reset fail count on successful login
AXES_ENABLE_ADMIN = True         # Let admin view/clear lockouts
AXES_USERNAME_CALLABLE = None    # Use username field as-is

# ── 7. File Upload Security ───────────────────────────────────────────────────
# Max upload size: 5 MB — prevents DoS via giant uploads
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# ── 8. Allowed image types (enforced in forms) ────────────────────────────────
ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp']

# ─── TWILIO (SMS Notifications) ──────────────────────────────────────────────
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', '')

# ─── DJANGO-ALLAUTH (Google OAuth) ──────────────────────────────────────────
ACCOUNT_LOGIN_ON_SIGNUP = True
ACCOUNT_LOGIN_METHODS = {'email', 'username'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'none'
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_LOGIN_ON_GET = False
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'APP': {
            'client_id': os.environ.get('GOOGLE_CLIENT_ID', ''),
            'secret': os.environ.get('GOOGLE_CLIENT_SECRET', ''),
        },
    }
}
