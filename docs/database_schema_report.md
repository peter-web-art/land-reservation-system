# Database Schema Report

**Date:** May 12, 2026  
**Project:** Land Reservation System  
**Database Default:** SQLite (`db.sqlite3`)

## Overview

The schema supports a role-based land marketplace with listing management, reservations, payment-proof tracking, user messaging, wishlists, notifications, and lightweight platform settings.

## Core Tables

### `users`

Custom authentication table from `accounts.User`.

| Field | Type | Notes |
| :--- | :--- | :--- |
| `id` | PK | Primary key |
| `username` | String | Unique login name |
| `password` | String | Django password hash |
| `role` | Choice | `customer`, `owner`, `admin` |
| `is_owner` | Boolean | Owner capability flag |
| `is_verified` | Boolean | Owner verification marker |
| `is_suspended` | Boolean | Blocks login |
| `created_on` / `updated_on` | DateTime | Audit timestamps |

### `accounts_personaldetails`

Extended one-to-one profile details for a user.

| Field | Type | Notes |
| :--- | :--- | :--- |
| `user_id` | FK | Unique link to `users` |
| `fname`, `mname`, `surname` | String | Personal names |
| `address` | Text | Optional |
| `phone` | String | Optional |
| `email` | Email | Optional |
| `photo_path` | Image | Uploaded profile image |
| `bio` | Text | Optional |

### `accounts_systemsettings`

Platform-level settings used by the admin portal.

| Field | Type | Notes |
| :--- | :--- | :--- |
| `maintenance_mode` | Boolean | Site maintenance toggle |
| `email_notifications` | Boolean | Global email toggle |
| `last_backup` | DateTime | Optional tracking field |

### `lands_land`

Primary listing table.

| Field | Type | Notes |
| :--- | :--- | :--- |
| `id` | PK | Primary key |
| `land_id` | String | Human-readable unique reference |
| `owner_id` | FK | Link to `users` |
| `title` | String | Listing title |
| `description` | Text | Optional content |
| `region`, `district`, `ward`, `street` | String | Structured location |
| `location` | String | Derived searchable location string |
| `latitude`, `longitude` | Float | Optional map coordinates |
| `usage` | Choice | `rent` or `sale` |
| `size`, `size_unit` | Decimal / Choice | Land area |
| `land_use` | Choice | Agricultural, residential, commercial, industrial, mixed |
| `topography` | Choice | Terrain classification |
| `soil_fertility` | Choice | Crop suggestion input |
| `price`, `price_unit` | Decimal / Choice | Pricing basis |
| `weekly_discount`, `monthly_discount` | Decimal | Rent pricing discounts |
| `contact_phone`, `contact_email` | String / Email | Listing contact info |
| `land_image_path` | Image | Legacy/fallback image |
| `is_active`, `is_draft` | Boolean | Listing visibility state |
| `wizard_step` | Integer | Listing completion progress |
| `view_count` | Integer | Detail page view counter |

### `lands_landimage`

Gallery images for listings.

| Field | Type | Notes |
| :--- | :--- | :--- |
| `land_id` | FK | Link to `lands_land` |
| `image` | Image | Uploaded file |
| `position` | Choice | Orientation or capture angle |
| `caption` | String | Optional |
| `is_primary` | Boolean | Cover image marker |
| `order` | Integer | Sort order |

### `lands_utility`

Utility or amenity records.

| Field | Type | Notes |
| :--- | :--- | :--- |
| `name` | String | Unique utility label |
| `land` | FK nullable | Optional direct utility-to-land link |
| `description` | Text | Optional |
| `icon_class` | String | UI icon hint |

### `lands_land_utilities`

Implicit many-to-many join between lands and utilities through `Land.utilities`.

### `lands_reservation`

Reservation and payment-tracking table.

| Field | Type | Notes |
| :--- | :--- | :--- |
| `land_id` | FK | Link to listing |
| `customer_id` | FK nullable | Registered customer |
| `customer_name`, `customer_email`, `customer_phone` | String | Captured requester details |
| `start_date`, `end_date` | Date | Rental period fields |
| `status` | Choice | `pending`, `approved`, `rejected`, `cancelled` |
| `payment_status` | Choice | `unpaid`, `paid`, `refunded` |
| `payment_method` | Choice | Mobile money, bank, or cash |
| `payment_reference` | String | Submitted reference |
| `payment_receipt` | Image | Proof upload |
| `payment_date` | Date | Optional |
| `payment_confirmed` | Boolean | Owner confirmation flag |
| `amount_paid`, `agreed_price` | Decimal | Payment values |
| `requested_size` | Decimal | Partial reservation amount |
| `notes` | Text | Additional details |

Indexes exist for `(land, status, start_date, end_date)`, `(land, customer)`, and `customer_email`.

### `lands_wishlist`

Customer saved listings.

| Field | Type | Notes |
| :--- | :--- | :--- |
| `user_id` | FK | Link to `users` |
| `land_id` | FK | Link to `lands_land` |

Unique constraint: `(user_id, land_id)`

### `lands_message`

Direct user-to-user messaging.

| Field | Type | Notes |
| :--- | :--- | :--- |
| `sender_id` | FK | Message sender |
| `recipient_id` | FK | Message recipient |
| `land_id` | FK nullable | Optional listing context |
| `subject` | String | Optional |
| `body` | Text | Message content |
| `is_read` | Boolean | Read state |

### `lands_notification`

In-app notification store.

| Field | Type | Notes |
| :--- | :--- | :--- |
| `user_id` | FK | Notification recipient |
| `notification_type` | Choice | Booking, payment, message, or system |
| `title` | String | Notification headline |
| `message` | Text | Notification body |
| `link` | String | UI navigation target |
| `is_read` | Boolean | Read state |

## Key Relationships

1. One `User` can own many `Land` records.
2. One `Land` can have many `Reservation`, `LandImage`, `Message`, and `Wishlist` references.
3. One `User` can create many `Reservation`, `Wishlist`, `Message`, and `Notification` records.
4. `Land` and `Utility` are linked through a many-to-many relation.
5. `User` and `PersonalDetails` are linked one-to-one.

## Schema Notes

- Reservation availability is partly derived in application logic rather than enforced by database constraints.
- The schema supports both whole-land and partial-size reservations.
- Some operational workflows, such as listing reports and support requests, are currently log-based and do not yet have dedicated tables.
