# Land Reserve - Land Reservation System

A professional land rental and sales platform built with Django, featuring responsive design, Google Maps integration, and comprehensive management tools.

## Features

### For Customers
- Browse available lands (rent & sale)
- Search by location, price, size, and land use
- Interactive map view with markers
- Wishlist management
- Booking system with date selection
- Messaging system
- Customer dashboard

### For Land Owners
- Property listing management
- Calendar view for bookings
- Earnings tracking (monthly, weekly, all-time)
- Reservation management
- Gallery image upload
- KYC verification system

### For Admins
- User management (verify, suspend, promote)
- KYC review queue
- Platform statistics dashboard
- Land and booking oversight

## Tech Stack

- **Backend**: Django 4.x
- **Database**: SQLite (default), PostgreSQL (production)
- **Frontend**: HTML, CSS (Tailwind-style custom), JavaScript
- **Maps**: Google Maps API
- **Authentication**: Django AllAuth

## Getting Started

### Prerequisites
- Python 3.8+
- Django 4.x

### Installation

1. Clone the repository:
```bash
git clone https://github.com/peter-web-art/land-reservation-system.git
cd land-reservation-system
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run migrations:
```bash
python manage.py migrate
```

5. Create superuser:
```bash
python manage.py createsuperuser
```

6. Run development server:
```bash
python manage.py runserver
```

7. Visit http://127.0.0.1:8000

## Environment Variables

Create a `.env` file in the root directory:

```env
DEBUG=True
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1
GOOGLE_MAPS_API_KEY=your-google-maps-api-key
# Twilio SMS (optional)
TWILIO_ACCOUNT_SID=your-sid
TWILIO_AUTH_TOKEN=your-token
TWILIO_PHONE_NUMBER=your-number
```

## Project Structure

```
land-reservation-system/
├── accounts/          # User authentication & profiles
├── lands/            # Land listings & reservations
├── land_reservation/ # Django project settings
├── static/           # CSS, JS, images
├── templates/        # HTML templates
├── unused/           # Deprecated files
├── manage.py
└── requirements.txt
```

## Responsive Design

The system is fully responsive with mobile-first design:
- Mobile: < 640px (1 column grid)
- Tablet: 640px - 1024px (2 column grid)
- Desktop: > 1024px (3 column grid)

## API Endpoints

- `/` - Land listings
- `/search/` - Advanced search
- `/accounts/login/` - Authentication
- `/lands/dashboard/` - Owner dashboard
- `/lands/dashboard/customer/` - Customer dashboard
- `/accounts/admin/` - Admin portal
- `/lands/notifications/` - Notifications

## License

MIT License

## Contributing

Contributions are welcome! Please submit a pull request.