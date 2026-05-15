# Functional Requirements

## Document Control

- System: Land Reservation System
- Version: 1.0
- Date: May 12, 2026
- Basis: Current implementation in the repository

## Purpose

This document defines the functional requirements for the current Land Reservation System. It is intended to describe what the system must do for public visitors, customers, land owners, and administrators.

## Actors

- Public Visitor
- Customer
- Land Owner
- Administrator

## Functional Requirements

### FR-1 User Registration And Authentication

1. The system shall allow users to register an account using username, email, and password.
2. The system shall allow users to sign in through local authentication.
3. The system shall support Google OAuth sign-in through `django-allauth`.
4. The system shall prevent suspended users from authenticating.
5. The system shall provide password reset through Django authentication routes.

### FR-2 Role Management

1. The system shall support `customer`, `owner`, and `admin` roles.
2. The system shall allow a customer to upgrade to land owner status.
3. The system shall restrict owner-only and admin-only functions by role.
4. The system shall support session-based UI mode switching for owner-capable users where applicable.

### FR-3 Profile Management

1. The system shall allow authenticated users to edit profile information.
2. The system shall store extended personal details including names, address, phone, email, photo, and bio.
3. The system shall expose profile details for use in account and listing workflows.

### FR-4 Public Listing Discovery

1. The system shall display active land listings on the public landing page.
2. The system shall allow public visitors to open a listing detail page without authentication.
3. The system shall expose listing title, location, usage, size, price, images, and owner contact information where configured.
4. The system shall track listing view count.

### FR-5 Search And Filtering

1. The system shall allow filtering by usage type, land use, location, keyword, price range, and size range.
2. The system shall support availability-aware filtering.
3. The system shall provide live search results for listing lookup.
4. The system shall provide location autocomplete suggestions.
5. The system shall provide district lookup based on selected region.

### FR-6 Listing Management

1. The system shall allow land owners to create listings.
2. The system shall allow land owners to edit and delete their own listings.
3. The system shall support rent and sale listings.
4. The system shall store structured Tanzania location fields including region, district, ward, and street.
5. The system shall support listing utilities, topography, soil fertility, contact details, pricing, and gallery images.
6. The system shall support draft and active listing states.

### FR-7 Availability And Pricing

1. The system shall calculate current remaining land size for a listing.
2. The system shall prevent overbooking based on overlapping approved or pending reservations.
3. The system shall support partial-size reservations where requested size is less than or equal to available size.
4. The system shall calculate next available date for display.
5. The system shall calculate rental price using listing price unit and weekly or monthly discounts where applicable.

### FR-8 Reservation Submission

1. The system shall allow customers to submit reservation requests for active listings.
2. The system shall capture customer identity and contact details for each reservation.
3. The system shall capture rental start and end dates for rent listings.
4. The system shall capture requested size for partial bookings.
5. The system shall create reservations with an initial `pending` status.

### FR-9 Customer Reservation Management

1. The system shall allow customers to view their reservations.
2. The system shall allow customers to cancel their own reservations subject to workflow rules.
3. The system shall provide a customer dashboard and a separate booking-tracking view.

### FR-10 Owner Reservation Management

1. The system shall allow land owners to view reservations for their listings.
2. The system shall allow land owners to approve, reject, or cancel reservations.
3. The system shall provide a calendar view of reservation periods.
4. The system shall allow owners to record payment details on reservations.

### FR-11 Payment Proof Workflow

1. The system shall allow customers to submit payment method, reference, date, amount, and receipt image for a booking.
2. The system shall keep submitted payments unconfirmed until reviewed by the owner.
3. The system shall allow owners to confirm payment receipt.
4. The system shall update payment and reservation status after owner confirmation.

### FR-12 Wishlist

1. The system shall allow authenticated customers to save listings to a wishlist.
2. The system shall allow customers to remove listings from the wishlist.
3. The system shall prevent duplicate wishlist entries for the same user and listing.

### FR-13 Messaging

1. The system shall allow authenticated users to send direct messages to other users.
2. The system shall allow messages to optionally reference a specific land listing.
3. The system shall provide an inbox view and message thread view.
4. The system shall track message read status.

### FR-14 Notifications

1. The system shall create in-app notifications for relevant booking, payment, messaging, and system events.
2. The system shall provide a notification list for authenticated users.
3. The system shall allow users to mark notifications as read.

### FR-15 Trust And Support Features

1. The system shall allow authenticated users to report suspicious listings.
2. The system shall provide a help center form for support requests.
3. The system shall support owner verification status in the user model.

### FR-16 Administration

1. The system shall provide an admin portal for platform monitoring.
2. The system shall display user, owner, customer, listing, booking, and revenue summary information in the admin portal.
3. The system shall allow administrators to verify, suspend, unsuspend, reset password for, and delete eligible users.
4. The system shall allow administrators to approve or reject bookings.
5. The system shall allow administrators to toggle maintenance mode and email notifications.
6. The system shall allow administrators to export platform data in CSV format.

### FR-17 Security And Protection

1. The system shall rate-limit selected sensitive routes.
2. The system shall lock out repeated failed logins using `django-axes`.
3. The system shall validate safe redirects for return navigation.
4. The system shall enforce configured file upload limits and allowed image types.

## Out Of Scope For The Current Build

- Integrated online payment gateway settlement
- Full moderation case management for reported listings
- Dedicated ticketing module for help center requests
- Public review and rating system for owners or listings

## Assumptions

- The current implementation uses SQLite by default for local development.
- Server-rendered Django templates remain the main delivery mechanism.
- Notification delivery is primarily in-app even when future channels are configured.
