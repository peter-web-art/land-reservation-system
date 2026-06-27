# Database ER Diagram

Below is a Mermaid ER diagram representing the main Django models and their relationships found in the project (accounts, lands).

```mermaid
erDiagram
    USERS {
        int id PK
        varchar username
        varchar role
    }

    PERSONAL_DETAILS {
        int id PK
        int user_id FK
    }

    PAYMENT_DETAILS {
        int id PK
        int user_id FK
        varchar payment_method
        varchar account_identifier
    }

    OPERATOR_PAYMENT_CONFIG {
        int id PK
        varchar payment_method
        varchar account_identifier
    }

    LAND {
        int id PK
        int owner_id FK
        varchar title
    }

    UTILITY {
        int id PK
        varchar name
    }

    RESERVATION {
        int id PK
        int land_id FK
        int customer_id FK
        date start_date
        date end_date
    }

    PAYMENT_RECORD {
        int id PK
        int reservation_id FK
        decimal amount
        varchar status
    }

    WISHLIST {
        int id PK
        int user_id FK
        int land_id FK
    }

    MESSAGE {
        int id PK
        int sender_id FK
        int recipient_id FK
        int land_id FK (nullable)
    }

    NOTIFICATION {
        int id PK
        int user_id FK
    }

    LAND_REPORT {
        int id PK
        int land_id FK
        int reported_by_id FK
        int reviewed_by_id FK (nullable)
    }

    PERSONAL_DETAILS ||--|| USERS : "user (OneToOne)"
    PAYMENT_DETAILS ||--|| USERS : "user (OneToOne)"
    OPERATOR_PAYMENT_CONFIG }o--|| USERS : "created_by/updated_by via AuditBase"
    LAND }o--|| USERS : "owner (Many lands → one user)"
    LAND ||--o{ UTILITY : "utilities (ManyToMany)"
    RESERVATION }o--|| LAND : "land"
    RESERVATION }o--|| USERS : "customer"
    RESERVATION }o--|| OPERATOR_PAYMENT_CONFIG : "selected_operator_payment (nullable)"
    PAYMENT_RECORD }o--|| RESERVATION : "reservation"
    WISHLIST }o--|| USERS : "user"
    WISHLIST }o--|| LAND : "land"
    MESSAGE }o--|| USERS : "sender"
    MESSAGE }o--|| USERS : "recipient"
    MESSAGE }o--|| LAND : "land (optional)"
    NOTIFICATION }o--|| USERS : "user"
    LAND_REPORT }o--|| LAND : "land"
    LAND_REPORT }o--|| USERS : "reported_by"
    LAND_REPORT }o--|| USERS : "reviewed_by (nullable)"
```

Notes
- `AuditBase` (in `accounts.models`) adds `created_by` / `updated_by` FKs to `User` for many audit-enabled models; those relations are represented where relevant (e.g., `OperatorPaymentConfig`).
- `Land.utilities` is a ManyToMany to `Utility` (the code also contains a nullable FK from `Utility` to `Land`, which is used in certain contexts).
- `PaymentRecord` caches owner payout fields at confirmation time (`owner_name`, `owner_payment_method`, `owner_account_identifier`).

If you want:
- I can generate a PNG/SVG from this Mermaid diagram and save it to `docs/`.
- Or produce a PlantUML/Graphviz DOT file instead.
- Or expand the diagram with more fields (PK/FK names, indexes) per table.

Tell me which output you prefer and I'll generate it next.