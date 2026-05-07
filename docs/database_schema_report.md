# Database Schema Report: Land Reservation System

**Date:** April 18, 2026
**Project:** Land Reservation System (Django-based)

---

## 1. Overview
This report outlines the database schema for the Land Reservation System. The architecture is designed to manage users (Customers, Owners, Admins), property listings (Lands), and the booking lifecycle (Reservations).

---

## 2. Table Definitions

### 2.1 `accounts_user`
Stores user profile information and role-based access control.

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | PK | Primary Key |
| `username` | String | Unique login name |
| `role` | Choice | `customer`, `owner`, or `admin` |
| `is_owner` | Boolean | True if user is a land owner |
| `is_verified` | Boolean | Admin verification flag |
| `phone` | String | Contact number |
| `kyc_status` | Choice | Identity verification status |
| `kyc_document` | File | Identity proof |
| `is_suspended` | Boolean | Access restriction flag |

### 2.2 `lands_land`
Core table for property listings.

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | PK | Primary Key |
| `owner_id` | FK | Reference to `accounts_user` |
| `title` | String | Property title |
| `usage` | Choice | `rent` or `sale` |
| `price` | Decimal | Base price |
| `price_unit` | Choice | `month`, `year`, or `total` |
| `location` | String | Physical address/region |
| `latitude/long` | Float | GPS coordinates |
| `size` | Decimal | Surface area |
| `land_use` | Choice | `agricultural`, `residential`, etc. |
| `topography` | Choice | Terrain type (Flat, Sloped, Rolling, etc.) |
| `land_image_path` | String | Upload path: `lands/` |

### 2.3 `lands_reservation`
Tracks booking requests and payments.

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | PK | Primary Key |
| `land_id` | FK | Reference to `lands_land` |
| `customer_id` | FK | Reference to `accounts_user` |
| `start_date` | Date | Rental start |
| `end_date` | Date | Rental end |
| `status` | Choice | `pending`, `approved`, `rejected`, `cancelled` |
| `payment_status`| Choice | `unpaid`, `paid`, `refunded` |
| `agreed_price` | Decimal | Final price for the transaction |

### 2.4 `lands_utility` (New)
Categorized list of utilities and amenities.

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | PK | Primary Key |
| `name` | String | e.g., "Piped Water", "Solar Power", "Fiber Internet" |
| `icon_class` | String | CSS class for UI icons (FontAwesome) |

**Examples:** Water Access, Solar Power, Fiber Internet, Perimeter Wall, Road Access, Street Lights.

### 2.4 `lands_land_utilities`

---

## 3. Relationships

1. **User - Land (1:N):** A user (Owner) can list multiple properties.
2. **Land - Reservation (1:N):** A property tracks its history of bookings.
3. **User - Reservation (1:N):** A user (Customer) can have multiple reservations.
6. User - Land (M:N): Wishlist functionality (tracked via many-to-many junction).

---

## 4. Performance & Logic Enhancements
The following system optimizations and features are implemented:
- **Availability Tracking:** The system calculates the `next_available_date` based on the latest approved reservation, allowing customers to see exactly when a property becomes free.
- **Reservation Lookups:** Indexed on `(land, status, start_date, end_date)` for fast availability checks.
- **Security & Authentication:** 
    - **Google OAuth Integration:** Support for social login via `django-allauth`.
    - **Password Recovery:** Automated password reset mechanism via email.
- **Wishlist Integrity:** Unique constraint on `(user, land)`.
