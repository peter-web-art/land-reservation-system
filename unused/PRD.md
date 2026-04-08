# LandReserve — Product Requirements Document (PRD)

## 1. Overview

### Project Name
**LandReserve** — Fixed Land Reservation System

### Project Type
Full-stack web application (Django + SQLite/PostgreSQL)

### Core Functionality
LandReserve is a dual-role marketplace platform enabling land owners to list properties for rent or sale, while customers can browse, book, and manage reservations. The system includes built-in fraud prevention, SMS notifications, KYC verification, and a complete messaging system.

### Target Market
- **Primary:** Tanzania and East Africa (TIME_ZONE = Africa/Dar_es_Salaam)
- **Users:** Land owners, property seekers, customers, and platform administrators
- **Use Cases:** Agricultural land rental, residential property booking, commercial land leasing, land sales

### Technology Stack
| Component | Technology |
|-----------|------------|
| Backend | Django 4.2+ (Python 3.10+) |
| Database | SQLite (dev), PostgreSQL (prod) |
| Authentication | Django Auth + django-allauth (Google OAuth) |
| Security | django-axes, django-ratelimit, django-csp, bleach |
| SMS | Twilio API |
| File Storage | Cloudinary (production), Local filesystem (dev) |
| Maps | Leaflet.js + OpenStreetMap |
| Deployment | Render.com (recommended) |

---

## 2. User Roles & Permissions

### 2.1 Customer (Default Role)
- Browse and search land listings
- Book land for rent or purchase
- View and cancel own reservations
- Add/remove lands from wishlist
- Send/receive messages with owners
- Check booking status without account
- Submit support requests

### 2.2 Land Owner
- All customer permissions, plus:
- Create, edit, and delete land listings
- Manage bookings on own lands (approve/reject)
- Record payment information
- Submit KYC documents for verification
- View dashboard analytics (views, bookings, wishlists)

### 2.3 Admin
- Full access to Django admin panel
- In-app admin portal for user management
- Verify/unverify land owners
- Suspend/reactivate user accounts
- Approve/reject KYC documents
- View all users, lands, and reservations
- Access KYC documents and government letters

---

## 3. Core Features

### 3.1 Land Listings

#### Listing Types
| Field | Options |
|-------|---------|
| Listing Type | Rent, Sale |
| Land Use | Agricultural, Residential, Commercial, Industrial, Mixed Use |
| Size Unit | Acres, Hectares, Square Metres |
| Price Unit | Per Month, Per Year, Total (one-time) |

#### Pricing Features
- **Base Price:** Set per listing with flexible unit (month/year/total)
- **Weekly Discount:** Percentage discount for rentals of 1+ week (0-90%)
- **Monthly Discount:** Percentage discount for rentals of 1+ month (0-90%)
- **Duration Limits:** Minimum and maximum rental periods (rent only)
- **Dynamic Calculation:** Automatic price calculation based on date range and discounts

#### Listing Fields
- Title (max 200 chars)
- Description (unlimited)
- Location (city/area)
- GPS Coordinates (latitude/longitude for map pins)
- Contact phone and email
- Primary image (cover photo)
- Image gallery (multiple images per listing)
- Size and size unit
- Land use type

#### Listing Management
- View count tracking (auto-incremented on detail page visit)
- Availability status (Available/Booked)
- Active/inactive toggle (admin-editable)
- Similar listings suggestion (by location or land use)

### 3.2 Reservation System

#### Booking Flow
1. User selects dates (for rent) or initiates purchase (for sale)
2. Form validates: date range, minimum/maximum duration, availability conflicts
3. Reservation created with status "pending"
4. Owner receives notification and reviews booking
5. Owner approves or rejects the reservation
6. SMS notification sent to customer with result

#### Reservation Statuses
| Status | Description |
|--------|-------------|
| Pending | Awaiting owner approval |
| Approved | Confirmed by owner |
| Rejected | Declined by owner |
| Cancelled | Cancelled by customer or system |

#### Payment System
- **Payment Methods:** M-Pesa, Airtel Money, Tigo Pesa, Bank Transfer, Cash on Arrival
- **Payment Status:** Unpaid, Paid, Refunded
- **Payment Tracking:** Payment method, reference number, amount paid
- **Agreed Price:** Final negotiated price stored with reservation

#### Date Overlap Protection
- Prevents double-booking of same dates
- Both approved AND pending reservations block dates
- Conflict check performed before approval

#### Anti-Spam Booking Rules
- Owners cannot book their own listings
- Users cannot have multiple active/pending bookings for same land
- Sold lands cannot be re-booked

### 3.3 Search & Discovery

#### Search Filters
- Location (text search)
- Keyword search (title + description)
- Price range (min/max)
- Listing type (rent/sale)
- Land use type (agricultural/residential/etc.)
- Sort by: newest, price (low-high), price (high-low), size

#### Map Integration
- Interactive Leaflet map showing all listings with GPS coordinates
- Price markers on map pins
- Map visible on search results and land detail pages

#### Pagination
- 12 listings per page
- Full pagination controls

### 3.4 User Accounts

#### Registration
- Username, email, password
- First/last name (optional)
- Phone number (optional)
- Profile picture (optional)
- Bio (optional)
- Role selection: Customer or Land Owner
- Google OAuth (social login)

#### Profile Management
- Edit personal information
- Upload profile picture
- Change phone number
- Update bio

#### Authentication Features
- Rate-limited login (10 POST requests/minute per IP)
- Brute-force protection (5 failed attempts = 1-hour lockout)
- Suspended users cannot log in
- Session-based authentication with 1-week expiry
- CSRF protection on all forms

### 3.5 KYC (Know Your Customer) System

#### Required Documents
1. **KYC Document:** Government ID or land ownership proof (JPG, PNG, WebP, PDF — max 10MB)
2. **Barua ya Serikali za Mtaa:** Government letter from local authority
   - Must be dated within the last 2 months
   - Cannot be future-dated

#### KYC Status Flow
| Status | Description |
|--------|-------------|
| Not Submitted | Initial state |
| Pending Review | Documents submitted, awaiting admin |
| Approved | Verified owner, green badge displayed |
| Rejected | Documents invalid, must resubmit |

#### Owner Verification Benefits
- Green "Verified" badge on all listings
- Unverified owners show grey "Unverified" badge
- Helps customers identify trusted sellers

### 3.6 Messaging System

#### Features
- Private messaging between users
- Threaded conversations
- Message subjects (optional)
- Link messages to specific land listings
- Unread message counter
- Mark messages as read
- Inbox and sent folder views

#### Use Cases
- Customer inquiries about listings
- Negotiation between buyer and seller
- Post-booking communication

### 3.7 Wishlist

#### Functionality
- Add/remove lands from wishlist
- View all wishlisted lands
- Wishlist visible in customer dashboard
- Toggle via AJAX (no page reload)
- Wishlist indicator on listing cards

### 3.8 Mode Switching

#### Customer ↔ Owner Switch
- Users can switch between customer and owner modes
- Admin accounts cannot switch modes
- Session-based mode tracking
- AJAX-powered mode toggle

### 3.9 SMS Notifications (Twilio)

#### Automated SMS Messages
| Trigger | Recipient | Content |
|---------|-----------|---------|
| Booking Approved | Customer | Confirmation with dates and contact |
| Booking Rejected | Customer | Rejection notification |
| Booking Cancelled | Owner | Customer cancellation notice |

#### Configuration
- Twilio Account SID, Auth Token, Phone Number
- Graceful fallback if Twilio not configured (logs instead)
- Phone number validation (6-20 digits with +, -, spaces, parentheses)

### 3.10 Help Center

#### Features
- Contact form with fields: name, email, subject, category, message
- Categories: general, booking, payment, technical, scam_report, other
- Support email logging
- Email notification to support team
- Rate-limited (5 POST requests/minute per IP)

### 3.11 Reporting System

#### Listing Reports
- Any logged-in user can report suspicious listings
- Report reason (sanitized, max 500 chars)
- Reports logged for admin review
- No user-facing count or list of reports

### 3.12 Admin Portal

#### In-App Admin Features
- Dashboard with system statistics
- User management (verify, suspend, delete)
- KYC review interface
- Recent registrations and bookings
- Flagged/suspended accounts list

#### Admin Actions
| Action | Target | Effect |
|--------|--------|--------|
| Verify Owner | Land Owner | Sets is_verified=True, green badge |
| Unverify Owner | Verified Owner | Removes verification badge |
| Suspend User | Any User | Blocks login, sets is_active=False |
| Unsuspend User | Suspended User | Restores login access |
| Make Owner | Customer | Upgrades to owner role |
| Delete User | Non-admin User | Permanent account deletion |

---

## 4. Security Features

### 4.1 Input Sanitization
- All user inputs cleaned with bleach library
- HTML tags stripped from all text fields
- Maximum length enforced on all inputs
- SQL injection prevented via Django ORM

### 4.2 Rate Limiting
| Endpoint | Limit | Method |
|----------|-------|--------|
| Login | 10/minute | POST |
| Registration | 10/minute | POST |
| Search | 30/minute | GET |
| Booking | 10/minute | POST |
| Add Land | 20/minute | POST |
| Edit Land | 20/minute | POST |
| Help Center | 5/minute | POST |

### 4.3 Brute-Force Protection
- 5 failed login attempts triggers lockout
- 1-hour lockout duration
- Custom lockout page
- Reset on successful login
- Admin-accessible lockout management

### 4.4 Security Headers
| Header | Value |
|--------|-------|
| X-XSS-Protection | Enabled |
| X-Content-Type-Options | nosniff |
| X-Frame-Options | DENY |
| Referrer-Policy | strict-origin-when-cross-origin |
| Content-Security-Policy | Configured with allowlist |

### 4.5 File Upload Security
- Allowed types: JPG, PNG, WebP (images), PDF (KYC)
- Maximum size: 5MB (images), 10MB (documents)
- Content-type validation on upload

### 4.6 HTTPS Enforcement (Production)
- SECURE_SSL_REDIRECT
- HSTS header (1 year)
- Secure cookies for session and CSRF

---

## 5. Data Models

### 5.1 User (accounts.User)
```
- username (unique, 3-150 chars)
- email (unique)
- password (hashed)
- first_name, last_name
- role (customer/owner/admin)
- is_owner (boolean)
- is_verified (boolean)
- is_suspended (boolean)
- phone
- bio
- profile_picture
- kyc_document (file)
- kyc_status (not_submitted/pending/approved/rejected)
- kyc_notes
- govt_letter (file)
- govt_letter_date
- date_joined, last_login
```

### 5.2 Land (lands.Land)
```
- owner (FK to User)
- title, description, location
- latitude, longitude
- listing_type (rent/sale)
- size, size_unit
- land_use (agricultural/residential/etc.)
- price, price_unit
- weekly_discount, monthly_discount
- min_duration_days, max_duration_days
- contact_phone, contact_email
- image (cover photo)
- is_active
- view_count
- created_at
```

### 5.3 LandImage (lands.LandImage)
```
- land (FK to Land)
- image
- caption
- is_primary
- order
- created_at
```

### 5.4 Reservation (lands.Reservation)
```
- land (FK to Land)
- customer (FK to User, optional)
- customer_name, customer_email, customer_phone
- start_date, end_date
- status (pending/approved/rejected/cancelled)
- payment_status (unpaid/paid/refunded)
- payment_method
- payment_reference
- amount_paid, agreed_price
- notes
- booking_date
```

### 5.5 Wishlist (lands.Wishlist)
```
- user (FK to User)
- land (FK to Land)
- created_at
- unique_together: (user, land)
```

### 5.6 Message (lands.Message)
```
- sender (FK to User)
- recipient (FK to User)
- land (FK to Land, optional)
- subject
- body
- is_read
- created_at
```

---

## 6. API Endpoints

### 6.1 Public Pages
| URL | View | Description |
|-----|------|-------------|
| `/` | land_list | Browse all lands |
| `/lands/search/` | search_lands | Search with filters |
| `/lands/<id>/` | land_detail | Land detail page |
| `/lands/<id>/book/` | book_land | Booking form |
| `/lands/check-status/` | check_booking_status | Anonymous booking lookup |
| `/lands/<id>/report/` | report_listing | Report suspicious listing |
| `/lands/help/` | help_center | Help/contact form |

### 6.2 Customer-Only
| URL | View | Description |
|-----|------|-------------|
| `/lands/dashboard/customer/` | customer_dashboard | Customer dashboard |
| `/lands/reservations/` | my_reservations | View reservations |
| `/lands/reservations/<id>/cancel/` | cancel_reservation | Cancel booking |
| `/lands/wishlist/` | my_wishlist | View wishlist |
| `/lands/<id>/wishlist/` | toggle_wishlist | Add/remove wishlist |
| `/lands/messages/` | inbox | Message inbox |
| `/lands/messages/send/` | send_message | Send message |
| `/lands/messages/<user_id>/` | message_thread | View thread |

### 6.3 Owner-Only
| URL | View | Description |
|-----|------|-------------|
| `/lands/dashboard/` | owner_dashboard | Owner dashboard |
| `/lands/add/` | add_land | Create listing |
| `/lands/<id>/edit/` | edit_land | Edit listing |
| `/lands/<id>/delete/` | delete_land | Delete listing |
| `/lands/reservations/manage/` | reservations_management | Manage all bookings |
| `/lands/reservations/<id>/status/<action>/` | update_reservation_status | Approve/reject |
| `/lands/reservations/<id>/payment/` | mark_payment | Record payment |
| `/lands/switch-to-owner/` | switch_to_owner | Become owner |

### 6.4 Account Management
| URL | View | Description |
|-----|------|-------------|
| `/accounts/register/` | register | User registration |
| `/accounts/profile/edit/` | profile_edit | Edit profile |
| `/accounts/kyc/submit/` | submit_kyc | Submit KYC documents |
| `/accounts/admin-portal/` | admin_portal | Admin dashboard |
| `/accounts/admin-portal/<id>/action/` | admin_user_action | Admin user actions |
| `/accounts/kyc/<id>/review/` | review_kyc | Review KYC |
| `/admin/` | Django admin | Full admin panel |
| `/health/` | health_check | Health check endpoint |

---

## 7. Environment Variables

### Required for Production
```
SECRET_KEY=<random-50-char-string>
DEBUG=False
ALLOWED_HOSTS=<domain>
SECURE_SSL_REDIRECT=True
HSTS_SECONDS=31536000
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
CORS_ALLOWED_ORIGINS=<domain>
```

### Optional Services
```
TWILIO_ACCOUNT_SID=<twilio-sid>
TWILIO_AUTH_TOKEN=<twilio-token>
TWILIO_PHONE_NUMBER=<twilio-number>
EMAIL_HOST=<smtp-host>
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=<email>
EMAIL_HOST_PASSWORD=<app-password>
GOOGLE_CLIENT_ID=<google-client-id>
GOOGLE_CLIENT_SECRET=<google-client-secret>
DATABASE_URL=<postgresql-url> (for production)
```

---

## 8. Deployment Requirements

### 8.1 Recommended Platform
**Render.com** (free tier available)
- Web Service for the Django app
- PostgreSQL database (free tier)
- Auto-deploy from GitHub

### 8.2 Build Commands
```bash
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
```

### 8.3 Start Command
```bash
gunicorn land_reservation.wsgi:application
```

### 8.4 Media Files
For persistent file storage on cloud platforms, use Cloudinary:
- Cloud Name, API Key, API Secret required
- Automatic image optimization and CDN

---

## 9. Testing Checklist

### 9.1 Security Testing
- [ ] HTTPS works and HTTP redirects
- [ ] Login form rate-limited after 5 failed attempts
- [ ] Suspended users cannot log in
- [ ] Non-owners cannot access owner dashboard
- [ ] Invalid file types rejected on upload
- [ ] XSS prevention works
- [ ] Health check returns status

### 9.2 Core Functionality
- [ ] User registration with role selection
- [ ] Google OAuth login
- [ ] Create and view land listings
- [ ] Upload multiple images
- [ ] Search by location, price, type
- [ ] Book land with date selection
- [ ] Owner approves/rejects booking
- [ ] SMS sent on approval (if Twilio configured)
- [ ] Cancel pending/approved booking
- [ ] Anonymous booking status check
- [ ] Wishlist add/remove
- [ ] Send and receive messages
- [ ] Submit KYC documents
- [ ] Admin verify/unverify owners
- [ ] Admin suspend/unsuspend users
- [ ] Mode switching (customer/owner)

---

## 10. Future Enhancements (Not Implemented)

The following features are potential additions for future development:
- Payment gateway integration (M-Pesa STK Push)
- Calendar availability view
- Review and rating system
- Land comparison tool
- Export bookings to PDF/CSV
- Email templates for notifications
- Mobile app (React Native/Flutter)
- Multi-language support
- Commission/fee system for platform
- Land inspection scheduling
- Document signing integration

---

## 11. Glossary

| Term | Definition |
|------|------------|
| KYC | Know Your Customer — identity verification process |
| Barua ya Serikali za Mtaa | Letter from local government authority |
| AirCover | Placeholder for trust/safety features |
| Rate Limiting | Restricting number of requests per time period |
| Brute-Force Attack | Repeated login attempts to guess password |
| M-Pesa | Mobile money service common in East Africa |
| CSRF | Cross-Site Request Forgery attack prevention |
| CSP | Content Security Policy — browser security header |

---

*Document Version: 1.0*  
*Last Updated: April 2026*  
*System Status: Fully Implemented*
