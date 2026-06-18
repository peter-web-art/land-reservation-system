"""
Admin Payment Management Views
Handles payment confirmation, rejection, and tracking workflow
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import timedelta
from decimal import Decimal

from .decorators import admin_required
from lands.models import PaymentRecord, Reservation, Notification, Message
from accounts.models import User, SystemSettings, PaymentDetails, OperatorPaymentConfig
from .payment_forms import OwnerPaymentDetailsForm, OperatorPaymentConfigForm
from lands.services import release_matured_escrow_payments



def get_platform_fee_percentage():
    """Get current platform fee percentage from system settings."""
    settings_obj = SystemSettings.objects.first()
    if not settings_obj:
        settings_obj = SystemSettings.objects.create()
    return settings_obj.platform_fee_percentage or Decimal('0')


def apply_platform_fee(payment):
    """Apply platform fee calculation to payment record."""
    fee_rate = get_platform_fee_percentage()
    payment.platform_fee_rate = fee_rate
    payment.platform_fee_amount = round((payment.amount or Decimal('0')) * fee_rate / Decimal('100'), 2)
    return payment


def create_notification(user, notification_type, title, message, link=''):
    """Helper to create notifications for users."""
    Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link
    )


@login_required
@admin_required
def admin_payments_dashboard(request):
    """
    Admin payments management dashboard.
    Shows all pending payments submitted by customers.
    """
    # Get all payment records with their reservations and lands
    payments = (PaymentRecord.objects
                .select_related('reservation', 'reservation__land', 'reservation__customer')
                .order_by('-created_on'))
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter in ['submitted', 'confirmed', 'rejected']:
        payments = payments.filter(status=status_filter)
    
    # Search by reference number or customer name
    search = request.GET.get('search', '').strip()
    if search:
        payments = payments.filter(
            Q(payment_reference__icontains=search) |
            Q(reservation__customer__username__icontains=search) |
            Q(reservation__customer_name__icontains=search) |
            Q(reservation__land__title__icontains=search)
        )
    
    # Calculate statistics
    total_payments = PaymentRecord.objects.filter(status__in=['submitted', 'confirmed'])
    submitted_payments = payments.filter(status='submitted')
    confirmed_payments = payments.filter(status='confirmed')
    rejected_payments = payments.filter(status='rejected')
    
    submitted_total = submitted_payments.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    confirmed_total = confirmed_payments.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    held_in_escrow = confirmed_payments.filter(reservation__payment_confirmed=True).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')
    total_platform_fees = confirmed_payments.aggregate(
        total=Sum('platform_fee_amount')
    )['total'] or Decimal('0')
    
    # Pagination
    paginator = Paginator(payments, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    context = {
        'payments': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'status_filter': status_filter,
        'search': search,
        'submitted_count': submitted_payments.count(),
        'confirmed_count': confirmed_payments.count(),
        'rejected_count': rejected_payments.count(),
        'submitted_total': submitted_total,
        'confirmed_total': confirmed_total,
        'held_in_escrow': held_in_escrow,
        'total_platform_fees': total_platform_fees,
        'pending_review_count': submitted_payments.count(),
    }
    
    return render(request, 'accounts/admin_payments_dashboard.html', context)


@login_required
@admin_required
def admin_payment_detail(request, payment_id):
    """
    View details of a specific payment submission.
    Allows admin to confirm or reject the payment.
    """
    payment = get_object_or_404(
        PaymentRecord.objects.select_related(
            'reservation', 'reservation__land', 'reservation__customer'
        ),
        pk=payment_id
    )
    
    reservation = payment.reservation
    land = reservation.land
    customer = reservation.customer
    
    # Get other payments for this reservation
    related_payments = reservation.payments.exclude(pk=payment.pk).order_by('-created_on')[:10]
    
    context = {
        'payment': payment,
        'reservation': reservation,
        'land': land,
        'customer': customer,
        'related_payments': related_payments,
        'remaining_balance': reservation.remaining_balance,
        'payment_image': payment.payment_receipt.url if payment.payment_receipt else None,
    }
    
    return render(request, 'accounts/admin_payment_detail.html', context)


@login_required
@admin_required
@require_http_methods(['POST'])
def admin_confirm_payment(request, payment_id):
    """
    Admin confirms a customer-submitted payment.
    - Marks payment as confirmed
    - Calculates platform fee
    - Updates reservation status
    - Sends notifications to customer and owner
    """
    payment = get_object_or_404(PaymentRecord, pk=payment_id)
    reservation = payment.reservation
    
    if payment.status != 'submitted':
        messages.error(request, f'Cannot confirm payment with status "{payment.status}".')
        return redirect('accounts:admin_payment_detail', payment_id=payment.pk)
    
    # Admin notes/confirmation
    admin_notes = request.POST.get('admin_notes', '').strip()
    payment_method = request.POST.get('payment_method', '').strip() or payment.payment_method
    verified_reference = request.POST.get('verified_reference', '').strip()

    def normalize_reference(value):
        return ''.join(str(value).split()).upper()

    expected_reference = normalize_reference(payment.payment_reference)
    observed_reference = normalize_reference(verified_reference)

    if not verified_reference:
        messages.error(request, 'Enter the reference number you verified before confirming the payment.')
        return redirect('accounts:admin_payment_detail', payment_id=payment.pk)

    if expected_reference and observed_reference != expected_reference:
        messages.error(
            request,
            f"Reference mismatch. Submitted reference is {payment.payment_reference}, but you entered {verified_reference}."
        )
        return redirect('accounts:admin_payment_detail', payment_id=payment.pk)

    # Confirm the payment
    payment.status = 'confirmed'
    payment.confirmed_on = timezone.now()
    payment.updated_by = request.user
    if admin_notes:
        payment.notes = (payment.notes or '') + f'\n\n[Admin Confirmation - {timezone.now():%Y-%m-%d %H:%M}]: {admin_notes}'
    if payment_method:
        payment.payment_method = payment_method
    
    # Apply platform fee
    payment = apply_platform_fee(payment)
    # Cache owner payout/contact details so admin can act on payouts without extra lookups
    owner = reservation.land.owner
    try:
        # Preferred: owner's personal details and payment details
        owner_full = None
        owner_phone = None
        owner_email = None
        owner_pay_method = None
        owner_account = None
        if owner:
            personal = getattr(owner, 'personal_details', None)
            if personal:
                owner_full = f"{personal.fname} {personal.surname}" if personal.fname and personal.surname else owner.get_full_name() or owner.username
                owner_phone = personal.phone or owner.phone or None
                owner_email = personal.email or owner.email or None
            else:
                owner_full = owner.get_full_name() or owner.username
                owner_phone = owner.phone or None
                owner_email = owner.email or None

            payment_details = getattr(owner, 'payment_details', None)
            if payment_details:
                owner_pay_method = payment_details.get_payment_method_display() if hasattr(payment_details, 'get_payment_method_display') else payment_details.payment_method
                owner_account = payment_details.account_identifier or None

        if owner_full:
            payment.owner_name = owner_full
        if owner_phone:
            payment.owner_phone = owner_phone
        if owner_email:
            payment.owner_email = owner_email
        if owner_pay_method:
            payment.owner_payment_method = owner_pay_method
        if owner_account:
            payment.owner_account_identifier = owner_account
    except Exception:
        import logging
        logging.exception('Failed to cache owner payout details')

    payment.save()
    
    # Update reservation
    reservation.payment_status = 'paid' if reservation.remaining_balance <= 0 else 'unpaid'
    reservation.payment_confirmed = True
    reservation.payment_method = payment_method or reservation.payment_method
    reservation.payment_reference = payment.payment_reference
    reservation.updated_by = request.user
    
    # If payment covers full amount, approve the reservation
    if reservation.remaining_balance <= 0:
        reservation.status = 'approved'
        reservation.payment_confirmed = True
    
    reservation.save()
    
    # Notify customer
    if reservation.customer:
        # Notify customer that payment is confirmed and provide operator payment options
        active_configs = get_active_operator_payment_configs()
        cfg_count = active_configs.count()
        choose_link = f'/lands/reservations/{reservation.pk}/payment-options/'
        msg = (
            f"Your payment of Tsh {payment.amount:,.0f} for '{reservation.land.title}' has been confirmed by admin. "
            f"Please choose how you'd like to pay the operator. "
            f"{cfg_count} payment method{'s' if cfg_count != 1 else ''} available."
        )
        create_notification(
            user=reservation.customer,
            notification_type='payment_confirmed',
            title='Payment Confirmed — Choose Payment Method',
            message=msg,
            link=choose_link
        )
    
    # Notify land owner
    owner = reservation.land.owner
    if owner:
        create_notification(
            user=owner,
            notification_type='payment_confirmed',
            title='Customer Payment Confirmed',
            message=(
                f"Customer {reservation.customer.username if reservation.customer else reservation.customer_name} "
                f"paid Tsh {payment.amount:,.0f} for '{reservation.land.title}'. "
                f"Funds are held in escrow and will be released {payment.payout_release_available_on:%b %d, %Y} - "
                f"{payment.payout_release_due_on:%b %d, %Y}."
            ),
            link=f'/lands/reservations/'
        )
    
    messages.success(
        request,
        f'✅ Payment Tsh {payment.amount:,.0f} confirmed! Customer and owner have been notified.'
    )
    return redirect('accounts:admin_payments_dashboard')


@login_required
@admin_required
@require_http_methods(['POST'])
def admin_reject_payment(request, payment_id):
    """
    Admin rejects a customer-submitted payment.
    - Marks payment as rejected
    - Sends notification to customer to resubmit
    - Reservation remains awaiting payment
    """
    payment = get_object_or_404(PaymentRecord, pk=payment_id)
    reservation = payment.reservation
    land = reservation.land
    
    if payment.status != 'submitted':
        messages.error(request, f'Cannot reject payment with status "{payment.status}".')
        return redirect('accounts:admin_payment_detail', payment_id=payment.pk)
    
    # Get rejection reason
    rejection_reason = request.POST.get('rejection_reason', 'Payment reference could not be verified.').strip()
    
    # Reject the payment
    payment.status = 'rejected'
    payment.notes = (payment.notes or '') + f'\n\n[Admin Rejection - {timezone.now():%Y-%m-%d %H:%M}]: {rejection_reason}'
    payment.updated_by = request.user
    payment.save()
    
    # Notify customer
    if reservation.customer:
        create_notification(
            user=reservation.customer,
            notification_type='payment_rejected',
            title='Payment Reference Rejected',
            message=(
                f"We could not verify your payment reference for '{land.title}': {rejection_reason}\n\n"
                f"Please check your payment details and resubmit in the platform."
            ),
            link=f'/lands/payments/'
        )
    
    messages.warning(
        request,
        f"Payment rejected. Customer {reservation.customer_name or reservation.customer.username} has been notified to resubmit."
    )
    return redirect('accounts:admin_payments_dashboard')


@login_required
@admin_required
def admin_payment_analytics(request):
    """
    Analytics dashboard showing payment trends and statistics.
    """
    from django.db.models.functions import TruncDay, TruncMonth
    
    # Get date range for filtering
    days = request.GET.get('days', '30')
    try:
        days = int(days)
    except:
        days = 30
    
    start_date = timezone.now() - timedelta(days=days)
    
    # Daily payment submissions
    daily_submissions = (PaymentRecord.objects
                        .filter(created_on__gte=start_date)
                        .annotate(day=TruncDay('created_on'))
                        .values('day')
                        .annotate(count=Count('id'), total=Sum('amount'))
                        .order_by('day'))
    
    # Daily confirmations
    daily_confirmations = (PaymentRecord.objects
                          .filter(confirmed_on__gte=start_date, status='confirmed')
                          .annotate(day=TruncDay('confirmed_on'))
                          .values('day')
                          .annotate(count=Count('id'), total=Sum('amount'))
                          .order_by('day'))
    
    # Payment method breakdown
    method_breakdown = (PaymentRecord.objects
                       .filter(status='confirmed')
                       .values('payment_method')
                       .annotate(count=Count('id'), total=Sum('amount')))
    
    # Status breakdown
    total_submitted = PaymentRecord.objects.filter(status='submitted').count()
    total_confirmed = PaymentRecord.objects.filter(status='confirmed').count()
    total_rejected = PaymentRecord.objects.filter(status='rejected').count()
    
    # Average confirmation time
    confirmed_with_times = PaymentRecord.objects.filter(
        status='confirmed',
        created_on__isnull=False,
        confirmed_on__isnull=False
    )
    avg_confirmation_time = None
    if confirmed_with_times.exists():
        total_time = sum(
            (p.confirmed_on - p.created_on).total_seconds()
            for p in confirmed_with_times[:100]  # Sample for performance
        )
        avg_confirmation_time = total_time / min(100, confirmed_with_times.count())
        avg_confirmation_time = avg_confirmation_time / 3600  # Convert to hours
    
    context = {
        'days': days,
        'daily_submissions': list(daily_submissions),
        'daily_confirmations': list(daily_confirmations),
        'method_breakdown': list(method_breakdown),
        'total_submitted': total_submitted,
        'total_confirmed': total_confirmed,
        'total_rejected': total_rejected,
        'avg_confirmation_time': avg_confirmation_time,
    }
    
    return render(request, 'accounts/admin_payment_analytics.html', context)
    
    # Daily payment submissions
    daily_submissions = (PaymentRecord.objects
                        .filter(created_on__gte=start_date)
                        .annotate(day=TruncDay('created_on'))
                        .values('day')
                        .annotate(count=Count('id'), total=Sum('amount'))
                        .order_by('day'))
    
    # Daily confirmations
    daily_confirmations = (PaymentRecord.objects
                          .filter(confirmed_on__gte=start_date, status='confirmed')
                          .annotate(day=TruncDay('confirmed_on'))
                          .values('day')
                          .annotate(count=Count('id'), total=Sum('amount'))
                          .order_by('day'))
    
    # Payment method breakdown
    method_breakdown = (PaymentRecord.objects
                       .filter(status='confirmed')
                       .values('payment_method')
                       .annotate(count=Count('id'), total=Sum('amount')))
    
    # Status breakdown
    total_submitted = PaymentRecord.objects.filter(status='submitted').count()
    total_confirmed = PaymentRecord.objects.filter(status='confirmed').count()
    total_rejected = PaymentRecord.objects.filter(status='rejected').count()
    
    # Average confirmation time
    confirmed_with_times = PaymentRecord.objects.filter(
        status='confirmed',
        created_on__isnull=False,
        confirmed_on__isnull=False
    )
    avg_confirmation_time = None
    if confirmed_with_times.exists():
        total_time = sum(
            (p.confirmed_on - p.created_on).total_seconds()
            for p in confirmed_with_times[:100]  # Sample for performance
        )
        avg_confirmation_time = total_time / min(100, confirmed_with_times.count())
        avg_confirmation_time = avg_confirmation_time / 3600  # Convert to hours
    
    context = {
        'days': days,
        'daily_submissions': list(daily_submissions),
        'daily_confirmations': list(daily_confirmations),
        'method_breakdown': list(method_breakdown),
        'total_submitted': total_submitted,
        'total_confirmed': total_confirmed,
        'total_rejected': total_rejected,
        'avg_confirmation_time': avg_confirmation_time,
    }
    
    return render(request, 'accounts/admin_payment_analytics.html', context)


@login_required
@admin_required
def admin_escrow_tracker(request):
    """
    View showing funds currently held in escrow.
    Tracks when funds will be available for release to owners.
    """
    
    release_matured_escrow_payments(triggered_by=request.user)

    # Get all confirmed payments
    escrow_payments = (PaymentRecord.objects
                      .filter(status='confirmed', reservation__payment_confirmed=True)
                      .select_related('reservation', 'reservation__land', 'reservation__customer')
                      .order_by('confirmed_on'))
    
    # Group by payout status
    today = timezone.now()
    
    holding = []  # Currently held (< 1 day old)
    in_window = []  # In release window (1-7 days)
    overdue = []  # Past 7 days
    released = []  # Owner acknowledged receipt
    
    total_held = Decimal('0')
    total_available = Decimal('0')
    total_overdue = Decimal('0')
    
    for payment in escrow_payments:
        if payment.owner_received_on:
            released.append(payment)
        elif not payment.confirmed_on:
            continue
        elif today < payment.payout_release_available_on:
            holding.append(payment)
            total_held += payment.amount or Decimal('0')
        elif today <= payment.payout_release_due_on:
            in_window.append(payment)
            total_available += payment.amount or Decimal('0')
        else:
            overdue.append(payment)
            total_overdue += payment.amount or Decimal('0')
    
    context = {
        'holding_payments': holding,
        'in_window_payments': in_window,
        'overdue_payments': overdue,
        'released_payments': released,
        'total_held': total_held,
        'total_available': total_available,
        'total_overdue': total_overdue,
        'today': today,
    }
    
    return render(request, 'accounts/admin_escrow_tracker.html', context)


@login_required
@admin_required
def admin_release_payment(request, payment_id):
    """Mark the payment as released to owner (admin-forced)."""
    payment = get_object_or_404(PaymentRecord, pk=payment_id)
    if request.method == 'POST':
        owner = payment.reservation.land.owner
        payment.owner_received_on = timezone.now()
        payment.updated_by = request.user
        payment.save(update_fields=['owner_received_on', 'updated_by'])
        if owner:
            Notification.objects.create(
                user=owner,
                notification_type='payment_received',
                title='Escrow Released to You',
                message=(
                    f'Tsh {payment.owner_net_amount:,.0f} for "{payment.reservation.land.title}" was manually released '
                    f'to you by {request.user.get_full_name() or request.user.username}.'
                ),
                link='/accounts/owner/payments/'
            )
        messages.success(request, f'Payment {payment.payment_reference} marked as released to owner.')
    return redirect('accounts:admin_escrow_tracker')


@login_required
@admin_required
def admin_delay_payment(request, payment_id):
    """Delay the payout window by N days (operator selects days)."""
    payment = get_object_or_404(PaymentRecord, pk=payment_id)
    if request.method == 'POST':
        try:
            days = int(request.POST.get('days', 0))
        except (TypeError, ValueError):
            days = 0
        if days <= 0:
            messages.error(request, 'Please enter a valid number of days to delay.')
            return redirect('accounts:admin_escrow_tracker')
        # Move confirmed_on forward by `days` to delay release window
        if payment.confirmed_on:
            payment.confirmed_on = payment.confirmed_on + timedelta(days=days)
            payment.updated_by = request.user
            payment.save(update_fields=['confirmed_on', 'updated_by'])
            messages.success(request, f'Payout window for {payment.payment_reference} delayed by {days} days.')
        else:
            messages.error(request, 'Cannot delay a payment that is not confirmed.')
    return redirect('accounts:admin_escrow_tracker')


@login_required
@admin_required
def admin_refund_payment(request, payment_id):
    """Mark a payment/reservation as refunded and notify customer and owner.
    Note: actual money movement must be handled by payment gateway/process outside this view.
    """
    payment = get_object_or_404(PaymentRecord, pk=payment_id)
    if request.method == 'POST':
        reservation = payment.reservation
        # Mark reservation payment status as refunded
        reservation.payment_status = 'refunded'
        reservation.save(update_fields=['payment_status'])

        # Mark payment as rejected (legacy use) and record admin
        payment.status = 'rejected'
        payment.updated_by = request.user
        payment.save(update_fields=['status', 'updated_by'])

        # Notify customer
        customer = reservation.customer
        if customer:
            create_notification(
                customer,
                'payment',
                'Payment Refunded',
                f'Your payment {payment.payment_reference} has been refunded by the operator. Please contact support for details.',
                f'/accounts/my_reservations/'
            )

        # Notify owner/operator
        create_notification(
            payment.reservation.land.owner,
            'payment',
            'Payment Returned to Customer',
            f'Payment {payment.payment_reference} was returned to the customer by {request.user.get_full_name() or request.user.username}.',
            f'/accounts/admin-portal/payments/{payment.pk}/'
        )

        messages.success(request, f'Payment {payment.payment_reference} marked as refunded. Ensure external refund executed.')
    return redirect('accounts:admin_escrow_tracker')


@login_required
@admin_required
def admin_payment_requests(request):
    """List incoming messages/requests sent by owners to admins/operators."""
    msgs = Message.objects.filter(recipient=request.user).select_related('sender', 'land').order_by('-created_on')
    paginator = Paginator(msgs, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'accounts/admin_payment_requests.html', context)


@login_required
@admin_required
def admin_message_detail(request, message_id):
    """View a specific message and reply to the sender."""
    msg = get_object_or_404(Message, pk=message_id, recipient=request.user)
    if request.method == 'POST':
        reply_text = request.POST.get('reply', '').strip()
        if not reply_text:
            messages.error(request, 'Reply cannot be empty.')
            return redirect('accounts:admin_message_detail', message_id=msg.pk)
        # Create reply message
        reply = Message.objects.create(
            sender=request.user,
            recipient=msg.sender,
            land=msg.land,
            subject=f'Re: {msg.subject}' if msg.subject else 'Reply from Support',
            body=reply_text[:2000]
        )
        # Notify the original sender — link to their inbox thread with admin
        admin_user = request.user
        create_notification(
            msg.sender,
            'message_received',
            f'Reply from {admin_user.get_full_name() or admin_user.username}',
            reply_text[:200],
            f'/lands/messages/{admin_user.pk}/'
        )
        messages.success(request, f'Reply sent to {msg.sender.get_full_name() or msg.sender.username}.')
        return redirect('accounts:admin_message_detail', message_id=msg.pk)

    # mark as read
    if not msg.is_read:
        msg.is_read = True
        msg.save(update_fields=['is_read'])

    context = {'message': msg}
    return render(request, 'accounts/admin_message_detail.html', context)


# ═══════════════════════════════════════════════════════════════════════════════
# OWNER PAYMENT DETAILS MANAGEMENT VIEWS
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
def owner_payment_details(request):
    """
    View for owners to manage their payment details for receiving payouts.
    """
    if request.user.role != 'owner':
        messages.error(request, 'Only land owners can manage payment details.')
        return redirect('accounts:profile_edit')
    
    try:
        payment_details = PaymentDetails.objects.get(user=request.user)
    except PaymentDetails.DoesNotExist:
        payment_details = None
    
    if request.method == 'POST':
        form = OwnerPaymentDetailsForm(request.POST, instance=payment_details)
        if form.is_valid():
            payment_details = form.save(commit=False)
            payment_details.user = request.user
            payment_details.save()
            messages.success(request, 'Payment details updated successfully!')
            return redirect('accounts:owner_payment_details')
    else:
        form = OwnerPaymentDetailsForm(instance=payment_details)
    
    context = {
        'form': form,
        'payment_details': payment_details,
    }
    
    return render(request, 'accounts/owner_payment_details.html', context)


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN OPERATOR PAYMENT CONFIG VIEWS
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@admin_required
def admin_operator_payment_config(request):
    """
    View for admins to configure payment details where customers should pay.
    """
    configs = OperatorPaymentConfig.objects.all().order_by('priority')
    
    context = {
        'configs': configs,
    }
    
    return render(request, 'accounts/admin_operator_payment_config.html', context)


@login_required
@admin_required
def admin_operator_payment_config_add(request):
    """Add a new operator payment configuration."""
    if request.method == 'POST':
        form = OperatorPaymentConfigForm(request.POST)
        if form.is_valid():
            config = form.save(commit=False)
            config.created_by = request.user
            config.save()
            messages.success(request, f'{config.get_payment_method_display()} payment method added!')
            return redirect('accounts:admin_operator_payment_config')
    else:
        form = OperatorPaymentConfigForm()
    
    context = {'form': form, 'action': 'Add'}
    return render(request, 'accounts/admin_operator_payment_config_form.html', context)


@login_required
@admin_required
def admin_operator_payment_config_edit(request, config_id):
    """Edit an operator payment configuration."""
    config = get_object_or_404(OperatorPaymentConfig, id=config_id)
    
    if request.method == 'POST':
        form = OperatorPaymentConfigForm(request.POST, instance=config)
        if form.is_valid():
            config = form.save(commit=False)
            config.updated_by = request.user
            config.save()
            messages.success(request, f'{config.get_payment_method_display()} payment method updated!')
            return redirect('accounts:admin_operator_payment_config')
    else:
        form = OperatorPaymentConfigForm(instance=config)
    
    context = {'form': form, 'action': 'Edit', 'config': config}
    return render(request, 'accounts/admin_operator_payment_config_form.html', context)


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN OWNER PAYMENT DETAILS MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@admin_required
def admin_owner_payment_details(request):
    """
    View for admins to see all owner payment details and request/verify them.
    Shows which owners have submitted details, and allows approval/verification.
    """
    # Filter payment details by owner role
    payment_details = PaymentDetails.objects.filter(user__role='owner').select_related('user').order_by('-created_on')
    
    # Filter by verification status
    status_filter = request.GET.get('status', 'all')
    if status_filter == 'verified':
        payment_details = payment_details.filter(is_verified=True)
    elif status_filter == 'unverified':
        payment_details = payment_details.filter(is_verified=False)
    elif status_filter == 'no_details':
        # Owners with no payment details submitted
        owners_with_details = payment_details.values_list('user_id', flat=True)
        owners_without_details = User.objects.filter(role='owner', is_active=True).exclude(id__in=owners_with_details)
        context = {
            'payment_details': [],
            'owners_without_details': owners_without_details,
            'status_filter': status_filter,
            'status_choices': [
                ('all', 'All Owners'),
                ('verified', 'Details Verified'),
                ('unverified', 'Details Pending'),
                ('no_details', 'No Details Submitted'),
            ],
        }
        return render(request, 'accounts/admin_owner_payment_details.html', context)
    
    # Search by owner or account identifier
    search = request.GET.get('search', '')
    if search:
        payment_details = payment_details.filter(
            Q(user__username__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(account_identifier__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(payment_details, 15)
    page = request.GET.get('page', 1)
    page_obj = paginator.get_page(page)
    
    # Count statistics
    total_owners = User.objects.filter(role='owner', is_active=True).count()
    verified_count = PaymentDetails.objects.filter(user__role='owner', is_verified=True).count()
    unverified_count = PaymentDetails.objects.filter(user__role='owner', is_verified=False).count()
    no_details_count = total_owners - verified_count - unverified_count
    
    context = {
        'payment_details': page_obj,
        'search': search,
        'status_filter': status_filter,
        'total_owners': total_owners,
        'verified_count': verified_count,
        'unverified_count': unverified_count,
        'no_details_count': no_details_count,
        'status_choices': [
            ('all', 'All Owners'),
            ('verified', 'Details Verified'),
            ('unverified', 'Details Pending'),
            ('no_details', 'No Details Submitted'),
        ],
    }
    
    return render(request, 'accounts/admin_owner_payment_details.html', context)


@login_required
@admin_required
def admin_owner_payment_details_review(request, payment_detail_id):
    """
    View for admin to review a specific owner's payment details.
    Allows verification/approval of payout method.
    """
    payment_detail = get_object_or_404(PaymentDetails, id=payment_detail_id, user__role='owner')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'verify':
            payment_detail.is_verified = True
            payment_detail.verified_on = timezone.now()
            payment_detail.save()
            
            # Send notification to owner
            create_notification(
                payment_detail.user,
                'payment_verified',
                'Payment Details Verified',
                f'Your {payment_detail.get_payment_method_display()} details have been verified. You will receive payouts here.'
            )
            messages.success(request, f'Payment details for {payment_detail.user.username} verified!')
            return redirect('accounts:admin_owner_payment_details')
            
        elif action == 'reject':
            reason = request.POST.get('reason', '')
            payment_detail.is_verified = False
            payment_detail.save()
            
            # Send notification with reason
            create_notification(
                payment_detail.user,
                'payment_rejected',
                'Payment Details Rejected',
                f'Your payment details were rejected. Reason: {reason or "Please update and resubmit."}. Please update your details.'
            )
            messages.warning(request, f'Payment details rejected. Notification sent to {payment_detail.user.username}.')
            return redirect('accounts:admin_owner_payment_details')
        
        elif action == 'set_default':
            # Set this as default and unset others for this user
            PaymentDetails.objects.filter(user=payment_detail.user).update(is_default=False)
            payment_detail.is_default = True
            payment_detail.save()
            messages.success(request, f'Set as default payout method for {payment_detail.user.username}.')
            return redirect('accounts:admin_owner_payment_details')

        elif action == 'edit_payout':
            edit_form = OwnerPaymentDetailsForm(request.POST, instance=payment_detail)
            if edit_form.is_valid():
                edit_form.save()
                messages.success(request, f'Payment details for {payment_detail.user.username} successfully modified by admin.')
                return redirect('accounts:admin_owner_payment_details_review', payment_detail_id=payment_detail.id)
            else:
                messages.error(request, 'Please correct the errors in the form.')
                # Render the template with the invalid form
                other_methods = PaymentDetails.objects.filter(user=payment_detail.user).exclude(id=payment_detail.id)
                context = {
                    'payment_detail': payment_detail,
                    'other_methods': other_methods,
                    'edit_form': edit_form,
                }
                return render(request, 'accounts/admin_owner_payment_details_review.html', context)
    
    # Get other payment methods for this owner
    other_methods = PaymentDetails.objects.filter(user=payment_detail.user).exclude(id=payment_detail.id)
    edit_form = OwnerPaymentDetailsForm(instance=payment_detail)
    
    context = {
        'payment_detail': payment_detail,
        'other_methods': other_methods,
        'edit_form': edit_form,
    }
    
    return render(request, 'accounts/admin_owner_payment_details_review.html', context)
@admin_required
def admin_operator_payment_config_delete(request, config_id):
    """Delete an operator payment configuration."""
    config = get_object_or_404(OperatorPaymentConfig, id=config_id)
    method_name = config.get_payment_method_display()
    
    if request.method == 'POST':
        config.delete()
        messages.success(request, f'{method_name} payment method removed!')
        return redirect('accounts:admin_operator_payment_config')
    
    context = {'config': config}
    return render(request, 'accounts/admin_operator_payment_config_confirm_delete.html', context)


@login_required
@require_http_methods(['POST'])
@admin_required
def admin_operator_payment_config_toggle(request, config_id):
    """Toggle whether a payment method is active."""
    config = get_object_or_404(OperatorPaymentConfig, id=config_id)
    config.is_active = not config.is_active
    config.updated_by = request.user
    config.save()
    
    status = 'activated' if config.is_active else 'deactivated'
    messages.success(request, f'{config.get_payment_method_display()} has been {status}.')
    
    return redirect('accounts:admin_operator_payment_config')


def get_active_operator_payment_configs():
    """
    Helper function to get active operator payment configurations.
    Used to display payment instructions to customers.
    """
    return OperatorPaymentConfig.objects.filter(is_active=True).order_by('priority')


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
# OWNER PAYMENT DASHBOARD — Track received payments, escrow status, and request payouts
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

@login_required
def owner_payment_dashboard(request):
    """
    Owner dashboard showing all payments from their listings.
    Displays escrow status, release timeline, and communication options.
    """
    if request.user.role != 'owner':
        messages.error(request, "Only land owners can access this page.")
        return redirect('lands:home')
    
    release_matured_escrow_payments(triggered_by=request.user)

    # Get all payments for reservations of this owner's lands
    reservations = Reservation.objects.filter(land__owner=request.user)
    owner_payment_details = PaymentDetails.objects.filter(user=request.user, is_verified=True).first()
    payments = PaymentRecord.objects.filter(
        reservation__in=reservations,
        status='confirmed'  # Only show confirmed payments
    ).select_related('reservation', 'reservation__land', 'reservation__customer').order_by('-created_on')
    
    # Group payments by status
    now = timezone.now()
    held_payments = []
    available_payments = []
    released_payments = []
    
    for payment in payments:
        if payment.confirmed_on:
            available_on = payment.payout_release_available_on
            due_on = payment.payout_release_due_on
            
            if available_on > now:
                # Still in hold period
                held_payments.append({
                    'payment': payment,
                    'days_held': (now - payment.confirmed_on).days,
                    'days_until_release': (available_on - now).days,
                    'available_on': available_on
                })
            elif now < due_on:
                # Available for release
                available_payments.append({
                    'payment': payment,
                    'available_on': available_on,
                    'due_on': due_on,
                    'days_until_due': (due_on - now).days
                })
            else:
                # Past due date (overdue for release)
                released_payments.append({
                    'payment': payment,
                    'overdue_by': (now - due_on).days
                })
    
    # Calculate totals
    total_held = sum(p['payment'].amount for p in held_payments)
    total_available = sum(p['payment'].amount for p in available_payments)
    total_released = sum(p['payment'].amount for p in released_payments)
    
    # Calculate with fees
    total_held_net = sum(p['payment'].owner_net_amount for p in held_payments)
    total_available_net = sum(p['payment'].owner_net_amount for p in available_payments)
    
    # Pagination
    paginator = Paginator(payments, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'held_payments': held_payments,
        'available_payments': available_payments,
        'released_payments': released_payments,
        'page_obj': page_obj,
        'all_payments': payments,
        'total_held': total_held,
        'total_held_net': total_held_net,
        'total_available': total_available,
        'total_available_net': total_available_net,
        'total_released': total_released,
        'held_count': len(held_payments),
        'available_count': len(available_payments),
        'released_count': len(released_payments),
        'owner_payment_details': owner_payment_details,
    }
    
    return render(request, 'accounts/owner_payment_dashboard.html', context)


@login_required
def owner_payment_detail(request, payment_id):
    """
    Owner detail view for a single payment.
    Shows escrow status, release timeline, and option to request from operator.
    """
    payment = get_object_or_404(PaymentRecord, pk=payment_id)
    
    # Verify owner owns the land in this reservation
    if payment.reservation.land.owner != request.user:
        messages.error(request, "You don't have permission to view this payment.")
        return redirect('accounts:owner_payment_dashboard')
    
    # Check payment status
    now = timezone.now()
    escrow_status = None
    days_held = None
    days_until_release = None
    days_until_due = None
    
    if payment.confirmed_on:
        available_on = payment.payout_release_available_on
        due_on = payment.payout_release_due_on
        
        if available_on > now:
            escrow_status = 'held'
            days_held = (now - payment.confirmed_on).days
            days_until_release = (available_on - now).days
        elif now < due_on:
            escrow_status = 'available'
            days_until_due = (due_on - now).days
        else:
            escrow_status = 'overdue'
            days_until_due = (now - due_on).days
    
    # Get operator payment configs to show where funds will go
    operator_configs = OperatorPaymentConfig.objects.filter(is_active=True).order_by('priority')
    
    # Get owner's payment details to show where they'll receive funds
    owner_payment_details = PaymentDetails.objects.filter(user=request.user, is_verified=True).first()
    
    # Get all historical payments on this reservation
    related_payments = PaymentRecord.objects.filter(
        reservation=payment.reservation
    ).exclude(pk=payment.pk).order_by('-created_on')[:5]
    
    context = {
        'payment': payment,
        'reservation': payment.reservation,
        'escrow_status': escrow_status,
        'days_held': days_held,
        'days_until_release': days_until_release,
        'days_until_due': days_until_due,
        'operator_configs': operator_configs,
        'owner_payment_details': owner_payment_details,
        'related_payments': related_payments,
        'now': now,
    }
    
    return render(request, 'accounts/owner_payment_detail.html', context)


# Owner request endpoint removed: payments and release are managed by admin/operator


@login_required
def owner_communication_list(request):
    """
    Show owner's communication history with operator about payments.
    """
    if request.user.role != 'owner':
        messages.error(request, "Only land owners can access this page.")
        return redirect('lands:home')
    
    # Get all notifications related to payments
    notifications = list(Notification.objects.filter(
        user=request.user,
        notification_type__in=['owner_payment_request', 'payment_request_sent', 'payment_released']
    ))

    # Get message threads between owner and admins/operators
    messages_qs = list(Message.objects.filter(
        Q(sender=request.user) | Q(recipient=request.user)
    ))

    # Combine and sort by created_on
    combined = sorted(notifications + messages_qs, key=lambda x: x.created_on, reverse=True)

    # Pagination
    paginator = Paginator(combined, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
    }
    
    return render(request, 'accounts/owner_communication.html', context)
