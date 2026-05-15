-- ============================================================================
-- Land Reservation System - Reference Schema
-- Updated: 2026-05-12
-- Source of truth: Django models in accounts/models.py and lands/models.py
-- ============================================================================

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    password VARCHAR(128) NOT NULL,
    last_login DATETIME NULL,
    is_superuser BOOLEAN NOT NULL DEFAULT 0,
    username VARCHAR(150) NOT NULL UNIQUE,
    first_name VARCHAR(150) NOT NULL DEFAULT '',
    last_name VARCHAR(150) NOT NULL DEFAULT '',
    email VARCHAR(254) NOT NULL DEFAULT '',
    is_staff BOOLEAN NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    date_joined DATETIME NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'customer',
    is_owner BOOLEAN NOT NULL DEFAULT 0,
    is_verified BOOLEAN NOT NULL DEFAULT 0,
    is_suspended BOOLEAN NOT NULL DEFAULT 0,
    created_by_id INTEGER NULL,
    created_on DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by_id INTEGER NULL,
    updated_on DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (updated_by_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE accounts_personaldetails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    fname VARCHAR(100) NOT NULL,
    mname VARCHAR(100) NOT NULL DEFAULT '',
    surname VARCHAR(100) NOT NULL,
    address TEXT NOT NULL DEFAULT '',
    phone VARCHAR(20) NOT NULL DEFAULT '',
    email VARCHAR(254) NOT NULL DEFAULT '',
    photo_path VARCHAR(100) NULL,
    bio TEXT NOT NULL DEFAULT '',
    created_by_id INTEGER NULL,
    created_on DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by_id INTEGER NULL,
    updated_on DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (updated_by_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE accounts_systemsettings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    maintenance_mode BOOLEAN NOT NULL DEFAULT 0,
    email_notifications BOOLEAN NOT NULL DEFAULT 1,
    last_backup DATETIME NULL
);

CREATE TABLE lands_land (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    land_id VARCHAR(20) NULL UNIQUE,
    owner_id INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT NULL,
    region VARCHAR(30) NOT NULL DEFAULT '',
    district VARCHAR(100) NOT NULL DEFAULT '',
    ward VARCHAR(100) NOT NULL DEFAULT '',
    street VARCHAR(100) NOT NULL DEFAULT '',
    location VARCHAR(200) NOT NULL DEFAULT '',
    latitude REAL NULL,
    longitude REAL NULL,
    usage VARCHAR(10) NOT NULL DEFAULT 'rent',
    size DECIMAL(10,2) NULL,
    size_unit VARCHAR(10) NOT NULL DEFAULT 'acres',
    land_use VARCHAR(20) NOT NULL DEFAULT 'agricultural',
    topography VARCHAR(20) NOT NULL DEFAULT 'flat',
    soil_fertility VARCHAR(20) NOT NULL DEFAULT 'moderate',
    additional_utilities_notes TEXT NULL,
    price DECIMAL(12,2) NULL,
    price_unit VARCHAR(10) NOT NULL DEFAULT 'month',
    weekly_discount DECIMAL(5,2) NOT NULL DEFAULT 0,
    monthly_discount DECIMAL(5,2) NOT NULL DEFAULT 0,
    contact_phone VARCHAR(20) NULL,
    contact_email VARCHAR(254) NULL,
    land_image_path VARCHAR(100) NULL,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    is_draft BOOLEAN NOT NULL DEFAULT 0,
    wizard_step INTEGER UNSIGNED NOT NULL DEFAULT 1,
    view_count INTEGER UNSIGNED NOT NULL DEFAULT 0,
    created_by_id INTEGER NULL,
    created_on DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by_id INTEGER NULL,
    updated_on DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (updated_by_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE lands_landimage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    land_id INTEGER NOT NULL,
    image VARCHAR(100) NOT NULL,
    position VARCHAR(20) NOT NULL DEFAULT 'other',
    caption VARCHAR(200) NOT NULL DEFAULT '',
    is_primary BOOLEAN NOT NULL DEFAULT 0,
    order INTEGER UNSIGNED NOT NULL DEFAULT 0,
    created_by_id INTEGER NULL,
    created_on DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by_id INTEGER NULL,
    updated_on DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (land_id) REFERENCES lands_land(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (updated_by_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE lands_utility (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    land_id INTEGER NULL,
    description TEXT NULL,
    icon_class VARCHAR(50) NULL,
    created_by_id INTEGER NULL,
    created_on DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by_id INTEGER NULL,
    updated_on DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (land_id) REFERENCES lands_land(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (updated_by_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE lands_land_utilities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    land_id INTEGER NOT NULL,
    utility_id INTEGER NOT NULL,
    UNIQUE (land_id, utility_id),
    FOREIGN KEY (land_id) REFERENCES lands_land(id) ON DELETE CASCADE,
    FOREIGN KEY (utility_id) REFERENCES lands_utility(id) ON DELETE CASCADE
);

CREATE TABLE lands_reservation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    land_id INTEGER NOT NULL,
    customer_id INTEGER NULL,
    customer_name VARCHAR(100) NOT NULL DEFAULT '',
    customer_email VARCHAR(254) NOT NULL DEFAULT '',
    customer_phone VARCHAR(20) NULL,
    start_date DATE NULL,
    end_date DATE NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    payment_status VARCHAR(20) NOT NULL DEFAULT 'unpaid',
    payment_method VARCHAR(20) NULL,
    payment_reference VARCHAR(100) NULL,
    payment_receipt VARCHAR(100) NULL,
    payment_date DATE NULL,
    payment_confirmed BOOLEAN NOT NULL DEFAULT 0,
    amount_paid DECIMAL(12,2) NULL,
    agreed_price DECIMAL(12,2) NULL,
    requested_size DECIMAL(10,2) NULL,
    notes TEXT NOT NULL DEFAULT '',
    created_by_id INTEGER NULL,
    created_on DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by_id INTEGER NULL,
    updated_on DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (land_id) REFERENCES lands_land(id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (updated_by_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX idx_reservation_availability
    ON lands_reservation (land_id, status, start_date, end_date);

CREATE INDEX idx_reservation_land_customer
    ON lands_reservation (land_id, customer_id);

CREATE INDEX idx_reservation_email
    ON lands_reservation (customer_email);

CREATE TABLE lands_wishlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    land_id INTEGER NOT NULL,
    created_by_id INTEGER NULL,
    created_on DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by_id INTEGER NULL,
    updated_on DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, land_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (land_id) REFERENCES lands_land(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (updated_by_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE lands_message (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL,
    recipient_id INTEGER NOT NULL,
    land_id INTEGER NULL,
    subject VARCHAR(200) NOT NULL DEFAULT '',
    body TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT 0,
    created_by_id INTEGER NULL,
    created_on DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by_id INTEGER NULL,
    updated_on DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (recipient_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (land_id) REFERENCES lands_land(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (updated_by_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE lands_notification (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    notification_type VARCHAR(30) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    link VARCHAR(200) NOT NULL DEFAULT '',
    is_read BOOLEAN NOT NULL DEFAULT 0,
    created_by_id INTEGER NULL,
    created_on DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by_id INTEGER NULL,
    updated_on DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (updated_by_id) REFERENCES users(id) ON DELETE SET NULL
);
