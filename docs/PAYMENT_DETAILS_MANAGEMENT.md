# Payment Details Management System - Implementation Guide

## Overview

This system manages payment details at two levels:

1. **Operator Payment Configuration** - Where customers send payments (configured by admin)
2. **Owner Payment Details** - Where owners receive payouts (configured by owners)

This ensures:
- Customers know exactly where to send payment
- System automatically uses owner's payment details when releasing escrowed funds
- Admin can verify all payment details before processing

## System Flow

### Customer Payment Submission Flow
```
Customer Views Land
    ↓
Clicks "Book Now"
    ↓
Checkout displays:
    - Available payment methods (from Operator Payment Config)
    - Payment details (M-Pesa number, Bank Account, etc.)
    - Payment instructions
    ↓
Customer sends payment
    ↓
Submits receipt/proof with reference number
    ↓
Admin reviews and confirms
```

### Payment Release to Owner Flow
```
Admin confirms payment
    ↓
Platform fee deducted automatically
    ↓
Funds held in escrow 24 hours
    ↓
After 24 hours:
    - Check owner's payment details
    - If verified: mark as available for release
    - If not verified: prompt admin to request details
    ↓
Owner receives payout automatically
```

## Models

### OperatorPaymentConfig
Stores payment methods where customers send money.

**Fields:**
- `payment_method` - M-Pesa, Airtel Money, Bank Transfer, etc.
- `account_identifier` - Phone number or account number
- `account_holder_name` - Business/operator name
- `bank_name` - Bank name (for bank transfers)
- `bank_branch` - Bank branch (for bank transfers)
- `instructions` - Payment instructions for customers
- `is_active` - Whether this method is available
- `priority` - Display order (lower = higher priority)

**Example:**
```
M-Pesa: +255 123 456 789 (operator account)
Bank Transfer: Account 12345678 at NMB Bank
Airtel Money: +255 987 654 321
```

### PaymentDetails (linked to User/Owner)
Stores payment details where owners want to receive payouts.

**Fields:**
- `payment_method` - Owner's preferred method
- `account_identifier` - Owner's account/phone number
- `account_holder_name` - Owner's name on account
- `bank_name` - Bank name (if applicable)
- `is_verified` - Admin has verified these details
- `is_default` - Use this as default for payouts

**Example:**
```
Owner: John Doe
M-Pesa: +255 111 222 333
Status: Verified by admin
```

## Features

### 1. Admin Operator Payment Configuration

**Access:** `/accounts/admin-portal/payment-config/`

**Capabilities:**
- Add new payment methods customers can use
- Edit existing payment methods
- Activate/deactivate payment methods
- Set display priority
- Add payment instructions
- View all configured methods

**Workflow:**
1. Admin logs in to Admin Portal
2. Click "Payment Config" tab
3. Click "Add Payment Method"
4. Configure payment details
5. Save (customers can now use it)

### 2. Owner Payment Details Management

**Access:** `/accounts/payment-details/`

**Capabilities:**
- Owners add/update payment details
- Multiple payment methods support
- Admin verification status visible
- Default method selection

**Workflow:**
1. Owner logs in
2. Go to Profile → Payment Details
3. Enter preferred payment method and account
4. Save
5. Admin verifies in admin panel
6. Owner receives payouts to this account

### 3. Admin Payment Release with Owner Details

**When releasing escrow funds:**
1. Admin opens payment detail view
2. System shows:
   - Owner's payment details (auto-populated)
   - Owner's verification status
   - Amount to be released
3. If owner not verified: show warning
4. If verified: can mark as ready to release
5. Funds transfer automatically

## URL Endpoints

### Admin Payment Configuration
```
/accounts/admin-portal/payment-config/                    # List all
/accounts/admin-portal/payment-config/add/                # Add new
/accounts/admin-portal/payment-config/<id>/edit/          # Edit
/accounts/admin-portal/payment-config/<id>/delete/        # Delete
/accounts/admin-portal/payment-config/<id>/toggle/        # Activate/Deactivate
```

### Owner Management
```
/accounts/payment-details/                                 # View/Edit owner details
```

### Django Admin
```
/admin/accounts/operatorpaymentconfig/                     # Admin interface
/admin/accounts/paymentdetails/                            # Admin interface
```

## Forms

### OwnerPaymentDetailsForm
- Validates account holder name and account identifier
- For bank transfers: requires bank name
- Mobile money methods: optional bank fields

### OperatorPaymentConfigForm
- Validates account details
- Requires payment method and account
- For bank transfers: requires bank name
- Supports priority ordering

## Views & Logic

### Helper Function
```python
def get_active_operator_payment_configs():
    """Get payment methods customers can use"""
    return OperatorPaymentConfig.objects.filter(is_active=True).order_by('priority')
```

## Admin Interface Features

### Operator Payment Config Admin
- List display: Payment method badge, account, status, priority
- Filters: By method, status, date
- Search: Account, holder name, bank
- Inline editing: Priority and active status
- Color-coded badges for each payment method

### Payment Details Admin
- List display: User, payment method badge, account, verification status
- Filters: By method, verification status, date
- Search: Username, account identifier
- Shows verification date and who verified

## Security Considerations

✓ Only admins can create/edit operator payment configs
✓ Only owners can edit their own payment details
✓ Verification status visible to all (requires admin approval)
✓ No direct modification of payment details once verified
✓ Audit trail: Created by, Updated by, timestamps
✓ Form validation on all inputs

## Integration with Existing System

### When Confirming Payment:
1. Admin reviews payment
2. Customer info displayed
3. Amount and platform fee shown
4. Owner's payment details retrieved (if verified)
5. On confirmation:
   - Platform fee applied
   - Escrow hold initiated
   - Funds scheduled for release to owner's account

### When Releasing Funds:
1. After 24-hour hold expires
2. Check if owner has verified payment details
3. If yes: initiate transfer to owner's account
4. If no: admin prompted to request details
5. Send notification to owner with transfer details

## Admin Portal Integration

Added to admin dashboard navigation:
- **Payments** - Payment confirmation/rejection
- **Payment Config** - Configure where customers pay

## Testing Checklist

- [ ] Admin can add payment methods
- [ ] Admin can edit payment methods
- [ ] Admin can activate/deactivate methods
- [ ] Methods display in priority order
- [ ] Owner can add payment details
- [ ] Owner can update payment details
- [ ] Admin can verify owner details
- [ ] Payment method badges display correctly
- [ ] Verification status shows in list
- [ ] Forms validate correctly
- [ ] Delete confirmation works
- [ ] Django admin shows all details

## Usage Examples

### Example 1: M-Pesa Setup

**Admin Configuration:**
- Payment Method: M-Pesa
- Account: +255 123 456 789
- Name: Land Reservation System
- Priority: 0 (highest)
- Instructions: "Send payment to +255 123 456 789 with reference [BOOKING_ID]"

**Customer Action:**
- Sees "M-Pesa: +255 123 456 789"
- Sends payment with reference
- Submits proof

**Admin Confirms:**
- Verifies payment
- Clicks confirm
- Deducts platform fee
- Holds funds in escrow

**After 24 hours:**
- Owner's M-Pesa: +255 111 222 333
- System transfers owner's share
- Owner receives SMS/notification

### Example 2: Bank Transfer Setup

**Admin Configuration:**
- Payment Method: Bank Transfer
- Account: 123-456-789-0
- Bank: NMB Bank
- Branch: Dar es Salaam
- Name: Land Rental Services Ltd

**Customer:**
- Sees bank transfer details
- Sends payment via bank
- Provides reference

**System Release:**
- Owner has bank account details verified
- After escrow hold: initiates bank transfer
- Owner receives funds in bank account

## Future Enhancements

1. **Automated Verification**
   - Verify M-Pesa/Airtel via API
   - Bank account verification

2. **Multi-Method Support**
   - Owners can register multiple accounts
   - Choose default for each land

3. **Payment Confirmation Notifications**
   - SMS to owner when funds available
   - Email with payment details
   - WhatsApp notifications

4. **Payout Scheduling**
   - Owners choose payment schedule
   - Weekly, monthly, or on-demand

5. **Payment Reconciliation**
   - Reports showing all transfers
   - Missing payments alerts
   - Audit trail export

## Support

For issues:
1. Check admin interface for payment configs
2. Verify owner payment details are set and verified
3. Review payment records in admin
4. Check escrow timeline
5. Verify system settings for fee percentage
