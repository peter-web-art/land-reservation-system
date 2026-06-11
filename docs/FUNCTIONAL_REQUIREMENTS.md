# Functional And Non-Functional Requirements

## Document Control

- System: Land Reservation System
- Scope: Current implemented functionality in this repository
- Version: 2.0
- Date: May 15, 2026

## Purpose

This document defines the functional and non-functional requirements currently supported by the system. It reflects the present application behavior as implemented in the Django codebase.

## Actors

- Public Visitor
- Customer
- Land Owner
- Administrator

## Functional Requirements

### FR-1 Account Registration And Authentication

1. The system shall allow users to register accounts using username, email, and password.
2. The system shall allow users to sign in using local authentication.
3. The system shall support Google OAuth sign-in through `django-allauth`.
4. The system shall allow password reset through Django authentication routes.
5. The system shall prevent suspended users from logging in.

### FR-2 Role And Access Management

1. The system shall support `customer`, `owner`, and `admin` roles.
2. The system shall allow customers to upgrade to owner status.
3. The system shall restrict owner-only and admin-only actions by role.
4. The system shall support session-based mode switching between customer and owner views for owner-capable users.
5. The system shall deny admin accounts from switching into owner/customer mode.

### FR-3 Profile Management

1. The system shall allow authenticated users to edit their profile details.
2. The system shall store extended personal details including names, address, phone, email, profile photo, and bio.
3. The system shall expose profile details for account and listing workflows.

### FR-4 Public Listing Discovery

1. The system shall display active land listings on the public landing page.
2. The system shall allow visitors to open land detail pages without authentication.
3. The system shall display listing title, location, usage, size, price, and images.
4. The system shall display owner contact details where configured.
5. The system shall track land detail page view counts.

### FR-5 Search And Filtering

1. The system shall allow filtering by usage type, land use, location, keyword, price range, and size range.
2. The system shall support availability-aware filtering.
3. The system shall provide live search results for listings.
4. The system shall provide location autocomplete suggestions.
5. The system shall provide district lookup based on selected region.

### FR-6 Listing Management

1. The system shall allow land owners to create land listings.
2. The system shall allow land owners to edit and delete their own listings.
3. The system shall support rent and sale listing types.
4. The system shall store structured Tanzania location fields including region, district, ward, and street.
5. The system shall support listing utilities, topography, soil fertility, pricing, contact details, and gallery images.
6. The system shall support draft and published listing states.

### FR-7 Availability And Pricing

1. The system shall calculate remaining land size for a listing.
2. The system shall prevent overbooking based on overlapping approved or pending reservations.
3. The system shall support partial-size reservations where requested size is less than or equal to available size.
4. The system shall calculate the next available date for a listing.
5. The system shall calculate rental price using listing price unit and configured discounts.

### FR-8 Reservation Submission

1. The system shall allow customers to submit reservation requests for active listings.
2. The system shall capture customer identity and contact details for each reservation.
3. The system shall capture rental start and end dates for rent reservations.
4. The system shall capture requested size for partial bookings.
5. The system shall create reservations with an initial `pending` status.

### FR-9 Customer Reservation Management

1. The system shall allow customers to view their reservations.
2. The system shall allow customers to cancel their own reservations according to workflow rules.
3. The system shall provide a customer dashboard and a booking tracking view.

### FR-10 Owner Reservation Management

1. The system shall allow land owners to view reservations for their listings.
2. The system shall allow land owners to approve, reject, or cancel reservations.
3. The system shall provide a calendar view of reservation periods.
4. The system shall allow owners to record payment details on reservations.

### FR-11 Manual Payment And Installment Tracking

1. The system shall allow customers to submit payment reference numbers for a booking.
2. The system shall allow customers to submit payment amount, payment method, payment date, and optional receipt evidence.
3. The system shall support multiple installment payments against one reservation.
4. The system shall calculate total confirmed amount paid for each reservation.
5. The system shall calculate the remaining balance for each reservation.
6. The system shall keep submitted payment records unconfirmed until the owner verifies them.
7. The system shall allow owners to confirm or reject submitted payment records.
8. The system shall update payment totals and balance after payment confirmation.

### FR-12 Platform Earnings And Commission Tracking

1. The system shall treat the administrator as the platform owner.
2. The system shall allow the administrator to configure a platform fee percentage.
3. The system shall calculate platform commission for each confirmed payment record.
4. The system shall calculate owner net payout after deducting the platform fee.
5. The system shall track platform earnings by owner and by property.
6. The system shall display confirmed gross revenue, platform earnings, and owner net totals in the admin portal.

### FR-13 Customer Payment Views

1. The system shall provide a Payments and Bills page for customers.
2. The system shall display total amount, confirmed paid amount, and remaining balance for each booking.
3. The system shall display payment history for each reservation.
4. The system shall allow customers to update payment references for unconfirmed installments.

### FR-14 Owner Payment Views

1. The system shall provide a Manage Payments page for owners.
2. The system shall display confirmed paid amount, platform fee, owner net, and remaining balance for each reservation.
3. The system shall display recent installment history.
4. The system shall allow owners to manually confirm payments when no customer reference exists.

### FR-15 Wishlist

1. The system shall allow authenticated customers to save listings to a wishlist.
2. The system shall allow customers to remove listings from the wishlist.
3. The system shall prevent duplicate wishlist entries for the same user and listing.

### FR-16 Messaging

1. The system shall allow authenticated users to send direct messages to other users.
2. The system shall allow messages to optionally reference a specific land listing.
3. The system shall provide an inbox view and a message thread view.
4. The system shall track message read status.

### FR-17 Notifications

1. The system shall create in-app notifications for booking, payment, messaging, and system events.
2. The system shall provide a notification list for authenticated users.
3. The system shall allow users to mark notifications as read.

### FR-18 Trust And Support

1. The system shall allow authenticated users to report suspicious listings.
2. The system shall provide a help center form for support requests.
3. The system shall support owner verification status in the user model.

### FR-19 Administration

1. The system shall provide an admin portal for platform monitoring.
2. The system shall display user, owner, customer, listing, booking, payment, and revenue summary information in the admin portal.
3. The system shall allow administrators to verify, suspend, unsuspend, reset password for, and delete eligible users.
4. The system shall allow administrators to approve or reject bookings.
5. The system shall allow administrators to toggle maintenance mode and email notifications.
6. The system shall allow administrators to configure the platform fee percentage.
7. The system shall allow administrators to export platform data in CSV format.

### FR-20 Security And Protection

1. The system shall rate-limit selected sensitive routes.
2. The system shall lock out repeated failed logins using `django-axes`.
3. The system shall validate safe redirects for return navigation.
4. The system shall enforce configured upload restrictions and allowed file types.
5. The system shall protect restricted actions using role-based access controls.

## Non-Functional Requirements

### NFR-1 Usability

1. The system shall provide a server-rendered user interface that is clear and consistent across customer, owner, and admin views.
2. The system shall present payment, booking, and earnings information in a way that is understandable to non-technical users.
3. The system shall keep common workflows accessible from dashboards and direct action buttons.

### NFR-2 Performance

1. The system shall respond acceptably for typical small-to-medium local deployment workloads.
2. The system shall use database indexes on common reservation lookups and account filters.
3. The system shall keep search and dashboard queries reasonably efficient for the current dataset size.

### NFR-3 Security

1. The system shall use authentication and authorization controls for protected operations.
2. The system shall prevent unsafe redirects and enforce route-level permissions.
3. The system shall limit abuse of sensitive routes through rate limiting and login lockout controls.
4. The system shall validate uploaded content types and file sizes where applicable.

### NFR-4 Reliability

1. The system shall preserve payment history and booking state in the database.
2. The system shall keep commission calculations tied to individual payment records so historical data remains stable if platform fees change later.
3. The system shall store confirmation and rejection events as durable application records.

### NFR-5 Maintainability

1. The system shall remain organized around Django apps for accounts and lands.
2. The system shall keep reusable payment and earnings logic in the model or view layer where it can be tested.
3. The system shall support automated regression tests for payment, admin earnings, and reservation workflows.

### NFR-6 Auditability

1. The system shall retain created and updated metadata for major records through the shared audit base model.
2. The system shall make it possible to review confirmed payments, owner earnings, and platform earnings by owner and by property.
3. The system shall preserve booking and payment history for later reporting.

### NFR-7 Compatibility

1. The system shall support current Django template-based rendering.
2. The system shall operate with SQLite in local development.
3. The system shall remain usable in modern browsers without requiring a separate frontend application.

### NFR-8 Deployability

1. The system shall run with the documented environment variables in `.env.example`.
2. The system shall support local development startup through `manage.py`.
3. The system shall rely on standard Django migration workflows for schema changes.

## Out Of Scope

- Full external payment gateway settlement
- A dedicated help desk/ticketing system
- Public review and rating system for owners or listings
- Complex accounting exports beyond current CSV support
- Mobile native applications

## Assumptions

1. Admin is treated as the system owner for platform earnings and configuration.
2. Payment tracking is reference-based and installment-based, not bank-API driven.
3. Server-rendered Django templates remain the primary UI pattern.
4. Local development uses SQLite unless configured otherwise.
