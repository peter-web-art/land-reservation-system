-- ============================================================================
-- LandReserve — Database Schema
-- Generated from Django models (accounts/models.py, lands/models.py)
-- Engine: SQLite 3 (default) | Compatible with PostgreSQL/MySQL
-- ============================================================================

-- ────────────────────────────────────────────────────────────────────────────
-- 1. USERS TABLE (Custom User — extends Django AbstractUser)
-- ────────────────────────────────────────────────────────────────────────────
-- ────────────────────────────────────────────────────────────────────────────
-- 1. USERS TABLE (Custom User — extends Django AbstractUser)
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    password        VARCHAR(128)  NOT NULL,
    last_login      DATETIME      NULL,
    is_superuser    BOOLEAN       NOT NULL DEFAULT 0,
    username        VARCHAR(150)  NOT NULL UNIQUE,
    is_staff        BOOLEAN       NOT NULL DEFAULT 0,
    is_active       BOOLEAN       NOT NULL DEFAULT 1,
    date_joined     DATETIME      NOT NULL,

    -- Custom fields
    role            VARCHAR(20)   NOT NULL DEFAULT 'customer',
        -- CHOICES: 'customer' = Customer, 'owner' = Land Owner, 'admin' = Admin
    is_owner        BOOLEAN       NOT NULL DEFAULT 0,
    is_verified     BOOLEAN       NOT NULL DEFAULT 0,
        -- Owner verified by admin — no scam risk
    is_suspended    BOOLEAN       NOT NULL DEFAULT 0,
        -- Suspended users cannot log in

    govt_letter      VARCHAR(100) NULL,
    govt_letter_date DATE         NULL,

    created_by_id     INTEGER       NULL,
    created_on        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by_id     INTEGER       NULL,
    updated_on        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_user_created_by
        FOREIGN KEY (created_by_id) REFERENCES users(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_user_updated_by
        FOREIGN KEY (updated_by_id) REFERENCES users(id)
        ON DELETE SET NULL
);


-- ────────────────────────────────────────────────────────────────────────────
-- 2. LAND TABLE (Core listing — rent or sale)
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE lands_land (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id          INTEGER       NOT NULL,
    title             VARCHAR(200)  NOT NULL,
    description       TEXT          NOT NULL,
    location          VARCHAR(200)  NOT NULL,
    latitude          REAL          NULL,
        -- GPS latitude for map pin
    longitude         REAL          NULL,
        -- GPS longitude for map pin
    usage             VARCHAR(10)   NOT NULL DEFAULT 'rent',
        -- CHOICES: 'rent' = Rent, 'sale' = Sale
    size              DECIMAL(10,2) NULL,
    size_unit         VARCHAR(10)   NOT NULL DEFAULT 'acres',
        -- CHOICES: 'acres', 'hectares', 'sqm'
    land_use          VARCHAR(20)   NOT NULL DEFAULT 'agricultural',
        -- CHOICES: 'agricultural', 'residential', 'commercial', 'industrial', 'mixed'

    -- 
    price             DECIMAL(12,2) NOT NULL,
        -- Base price in Tsh
    price_unit        VARCHAR(10)   NOT NULL DEFAULT 'month',
        -- CHOICES: 'month' = Per Month, 'year' = Per Year, 'total' = Total / One-time
    weekly_discount   DECIMAL(5,2)  NOT NULL DEFAULT 0,
        -- % discount for bookings of 1+ week (rent only)
    monthly_discount  DECIMAL(5,2)  NOT NULL DEFAULT 0,
        -- % discount for bookings of 1+ month (rent only)
    min_duration_days INTEGER UNSIGNED NOT NULL DEFAULT 1,
        -- Minimum rental period in days (rent listings only)
    max_duration_days INTEGER UNSIGNED NULL,
        -- Maximum rental period in days (NULL = no limit)

    contact_phone     VARCHAR(20)   NULL,
    contact_email     VARCHAR(254)  NULL,
    land_image_path   VARCHAR(100)  NULL,
        -- Upload path: lands/
    is_active         BOOLEAN       NOT NULL DEFAULT 1,
    view_count        INTEGER UNSIGNED NOT NULL DEFAULT 0,
        -- Number of detail page views

    created_by_id     INTEGER       NULL,
    created_on        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by_id     INTEGER       NULL,
    updated_on        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_land_owner
        FOREIGN KEY (owner_id) REFERENCES users(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_land_created_by
        FOREIGN KEY (created_by_id) REFERENCES users(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_land_updated_by
        FOREIGN KEY (updated_by_id) REFERENCES users(id)
        ON DELETE SET NULL
);


-- ────────────────────────────────────────────────────────────────────────────
-- 3. RESERVATIONS TABLE (Bookings linking customer → land)
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE lands_reservation (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    land_id           INTEGER       NOT NULL,
    customer_id       INTEGER       NULL,
    customer_name     VARCHAR(100)  NOT NULL DEFAULT '',
    customer_email    VARCHAR(254)  NOT NULL DEFAULT '',
    customer_phone    VARCHAR(20)   NULL,
    
    -- Date range (for rent bookings)
    start_date        DATE          NULL,
        -- Start date of rental period
    end_date          DATE          NULL,
        -- End date of rental period

    status            VARCHAR(20)   NOT NULL DEFAULT 'pending',
        -- CHOICES: 'pending', 'approved', 'rejected', 'cancelled'
    payment_status    VARCHAR(20)   NOT NULL DEFAULT 'unpaid',
        -- CHOICES: 'unpaid', 'paid', 'refunded'
    payment_method    VARCHAR(20)   NULL,
        -- CHOICES: 'mpesa' = M-Pesa, 'airtel' = Airtel Money,
        --          'tigopesa' = Tigo Pesa, 'bank' = Bank Transfer,
        --          'cash' = Cash on Arrival
    payment_reference VARCHAR(100)  NULL,
    amount_paid       DECIMAL(12,2) NULL,
    agreed_price      DECIMAL(12,2) NULL,
        -- Final agreed price for this booking
    notes             TEXT          NOT NULL DEFAULT '',
    created_by_id     INTEGER       NULL,
    created_on        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by_id     INTEGER       NULL,
    updated_on        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_reservation_land
        FOREIGN KEY (land_id) REFERENCES lands_land(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_reservation_customer
        FOREIGN KEY (customer_id) REFERENCES users(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_reservation_created_by
        FOREIGN KEY (created_by_id) REFERENCES users(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_reservation_updated_by
        FOREIGN KEY (updated_by_id) REFERENCES users(id)
        ON DELETE SET NULL
);

-- Performance indexes for reservation queries
CREATE INDEX idx_reservation_availability
    ON lands_reservation (land_id, status, start_date, end_date);
CREATE INDEX idx_reservation_land_customer
    ON lands_reservation (land_id, customer_id);
CREATE INDEX idx_reservation_email
    ON lands_reservation (customer_email);


-- ────────────────────────────────────────────────────────────────────────────
-- 5. WISHLIST TABLE (Saved/favorited lands per user)
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE lands_wishlist (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER  NOT NULL,
    land_id     INTEGER  NOT NULL,
    created_by_id     INTEGER       NULL,
    created_on        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by_id     INTEGER       NULL,
    updated_on        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_wishlist_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_wishlist_land
        FOREIGN KEY (land_id) REFERENCES lands_land(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_wishlist_created_by
        FOREIGN KEY (created_by_id) REFERENCES users(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_wishlist_updated_by
        FOREIGN KEY (updated_by_id) REFERENCES users(id)
        ON DELETE SET NULL,
    CONSTRAINT uq_wishlist_user_land
        UNIQUE (user_id, land_id)
);


-- ────────────────────────────────────────────────────────────────────────────
-- 6. MESSAGES TABLE (In-app messaging between users)
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE lands_message (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id     INTEGER       NOT NULL,
    recipient_id  INTEGER       NOT NULL,
    land_id       INTEGER       NULL,
        -- Optional: which land listing the message is about
    subject       VARCHAR(200)  NOT NULL DEFAULT '',
    body          TEXT          NOT NULL,
    is_read       BOOLEAN       NOT NULL DEFAULT 0,
    created_by_id     INTEGER       NULL,
    created_on        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by_id     INTEGER       NULL,
    updated_on        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_message_sender
        FOREIGN KEY (sender_id) REFERENCES users(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_message_recipient
        FOREIGN KEY (recipient_id) REFERENCES users(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_message_land
        FOREIGN KEY (land_id) REFERENCES lands_land(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_message_created_by
        FOREIGN KEY (created_by_id) REFERENCES users(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_message_updated_by
        FOREIGN KEY (updated_by_id) REFERENCES users(id)
        ON DELETE SET NULL
);


-- ────────────────────────────────────────────────────────────────────────────
-- 7. NOTIFICATIONS TABLE (System event notifications)
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE lands_notification (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id            INTEGER       NOT NULL,
    notification_type  VARCHAR(30)   NOT NULL,
        -- CHOICES: 'booking_new', 'booking_approved', 'booking_rejected',
        --          'booking_cancelled', 'payment_received', 'message_received',
        --          'payment', 'system'
    title              VARCHAR(200)  NOT NULL,
    message            TEXT          NOT NULL,
    link               VARCHAR(200)  NOT NULL DEFAULT '',
        -- URL to navigate to when clicked
    is_read            BOOLEAN       NOT NULL DEFAULT 0,
    created_by_id      INTEGER       NULL,
    created_on         DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by_id      INTEGER       NULL,
    updated_on         DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_notification_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_notification_created_by
        FOREIGN KEY (created_by_id) REFERENCES users(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_notification_updated_by
        FOREIGN KEY (updated_by_id) REFERENCES users(id)
        ON DELETE SET NULL
);


-- ────────────────────────────────────────────────────────────────────────────
-- 8. UTILITIES TABLE (Dynamic amenities/infrastructure)
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE lands_utility (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        VARCHAR(100)  NOT NULL UNIQUE,
    icon_class  VARCHAR(50)   NULL,
        -- CSS icon class (e.g., FontAwesome/Bootstrap Icons)

    -- Audit fields
    created_by_id     INTEGER       NULL,
    created_on        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by_id     INTEGER       NULL,
    updated_on        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_utility_created_by
        FOREIGN KEY (created_by_id) REFERENCES users(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_utility_updated_by
        FOREIGN KEY (updated_by_id) REFERENCES users(id)
        ON DELETE SET NULL
);


-- ────────────────────────────────────────────────────────────────────────────
-- 9. LAND UTILITIES LINK TABLE (Many-to-Many junction)
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE lands_land_utilities (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    land_id     INTEGER NOT NULL,
    utility_id  INTEGER NOT NULL,

    CONSTRAINT fk_land_utilities_land
        FOREIGN KEY (land_id) REFERENCES lands_land(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_land_utilities_utility
        FOREIGN KEY (utility_id) REFERENCES lands_utility(id)
        ON DELETE CASCADE,
    CONSTRAINT uq_land_utility
        UNIQUE (land_id, utility_id)
);


-- ────────────────────────────────────────────────────────────────────────────
-- 10. PERSONAL DETAILS TABLE (Extended user profiles)
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE accounts_personaldetails (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL UNIQUE,
    fname       VARCHAR(100) NOT NULL,
    mname       VARCHAR(100) NULL,
    surname     VARCHAR(100) NOT NULL,
    address     TEXT         NULL,
    phone       VARCHAR(20)  NULL,
    email       VARCHAR(254) NULL,
    photo_path  VARCHAR(100) NULL,
    bio         TEXT         NULL,

    -- Audit fields
    created_by_id     INTEGER       NULL,
    created_on        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by_id     INTEGER       NULL,
    updated_on        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_details_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_details_created_by
        FOREIGN KEY (created_by_id) REFERENCES users(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_details_updated_by
        FOREIGN KEY (updated_by_id) REFERENCES users(id)
        ON DELETE SET NULL
);


-- ============================================================================
-- DJANGO BUILT-IN TABLES (auto-generated by framework)
-- ============================================================================

-- User ↔ Group many-to-many
CREATE TABLE accounts_user_groups (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id  INTEGER NOT NULL,
    group_id INTEGER NOT NULL,

    CONSTRAINT fk_user_groups_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_user_groups_group
        FOREIGN KEY (group_id) REFERENCES auth_group(id)
        ON DELETE CASCADE,
    CONSTRAINT uq_user_groups
        UNIQUE (user_id, group_id)
);

-- User ↔ Permission many-to-many
CREATE TABLE accounts_user_user_permissions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL,
    permission_id INTEGER NOT NULL,

    CONSTRAINT fk_user_perms_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_user_perms_perm
        FOREIGN KEY (permission_id) REFERENCES auth_permission(id)
        ON DELETE CASCADE,
    CONSTRAINT uq_user_perms
        UNIQUE (user_id, permission_id)
);

-- Auth groups
CREATE TABLE auth_group (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(150) NOT NULL UNIQUE
);

-- Auth permissions
CREATE TABLE auth_permission (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            VARCHAR(255) NOT NULL,
    content_type_id INTEGER      NOT NULL,
    codename        VARCHAR(100) NOT NULL,

    CONSTRAINT fk_perm_content_type
        FOREIGN KEY (content_type_id) REFERENCES django_content_type(id)
        ON DELETE CASCADE,
    CONSTRAINT uq_perm
        UNIQUE (content_type_id, codename)
);

-- Group ↔ Permission many-to-many
CREATE TABLE auth_group_permissions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id      INTEGER NOT NULL,
    permission_id INTEGER NOT NULL,

    CONSTRAINT fk_group_perms_group
        FOREIGN KEY (group_id) REFERENCES auth_group(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_group_perms_perm
        FOREIGN KEY (permission_id) REFERENCES auth_permission(id)
        ON DELETE CASCADE,
    CONSTRAINT uq_group_perms
        UNIQUE (group_id, permission_id)
);

-- Django content types
CREATE TABLE django_content_type (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    app_label VARCHAR(100) NOT NULL,
    model     VARCHAR(100) NOT NULL,

    CONSTRAINT uq_content_type
        UNIQUE (app_label, model)
);

-- Django sessions
CREATE TABLE django_session (
    session_key  VARCHAR(40) PRIMARY KEY,
    session_data TEXT        NOT NULL,
    expire_date  DATETIME    NOT NULL
);

CREATE INDEX idx_session_expire ON django_session (expire_date);

-- Django admin log
CREATE TABLE django_admin_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    action_time     DATETIME      NOT NULL,
    object_id       TEXT          NULL,
    object_repr     VARCHAR(200)  NOT NULL,
    action_flag     SMALLINT UNSIGNED NOT NULL,
    change_message  TEXT          NOT NULL,
    content_type_id INTEGER       NULL,
    user_id         INTEGER       NOT NULL,

    CONSTRAINT fk_admin_log_content_type
        FOREIGN KEY (content_type_id) REFERENCES django_content_type(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_admin_log_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
);

-- Django migrations tracker
CREATE TABLE django_migrations (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    app     VARCHAR(255) NOT NULL,
    name    VARCHAR(255) NOT NULL,
    applied DATETIME     NOT NULL
);

-- Django sites framework
CREATE TABLE django_site (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    domain VARCHAR(100) NOT NULL UNIQUE,
    name   VARCHAR(50)  NOT NULL
);
