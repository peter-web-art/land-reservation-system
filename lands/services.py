from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from lands.models import Notification, PaymentRecord


def release_matured_escrow_payments(triggered_by=None):
    """
    Auto-release confirmed payments that have stayed in escrow for 24 hours or more.

    Returns a list of released PaymentRecord instances.
    """
    cutoff = timezone.now() - timezone.timedelta(hours=24)
    released_payments = []
    admins = User.objects.filter(Q(is_staff=True) | Q(role=User.ROLE_ADMIN), is_active=True)

    with transaction.atomic():
        eligible_payments = (
            PaymentRecord.objects
            .select_for_update()
            .select_related('reservation', 'reservation__land', 'reservation__land__owner', 'reservation__customer')
            .filter(status='confirmed', confirmed_on__lte=cutoff, owner_received_on__isnull=True)
            .order_by('confirmed_on')
        )

        for payment in eligible_payments:
            if triggered_by:
                payment.updated_by = triggered_by
            payment.owner_received_on = timezone.now()
            payment.save(update_fields=['owner_received_on', 'updated_by', 'updated_on'])
            released_payments.append(payment)

            owner = payment.reservation.land.owner if payment.reservation_id else None
            owner_name = (owner.get_full_name() or owner.username) if owner else 'Unknown owner'
            land_title = payment.reservation.land.title if payment.reservation_id else 'Unknown land'
            release_amount = payment.owner_net_amount

            if owner:
                Notification.objects.create(
                    user=owner,
                    notification_type='payment_received',
                    title='Escrow Released to You',
                    message=(
                        f'Tsh {release_amount:,.0f} for "{land_title}" has been automatically released to you '
                        f'after the 24-hour escrow window.'
                    ),
                    link=reverse('accounts:owner_payment_dashboard')
                )

            for admin in admins:
                Notification.objects.create(
                    user=admin,
                    notification_type='payment',
                    title='Escrow Auto-Released',
                    message=(
                        f'Tsh {release_amount:,.0f} for "{land_title}" was automatically released to '
                        f'{owner_name} after 24 hours.'
                    ),
                    link=reverse('accounts:admin_escrow_tracker')
                )

    return released_payments
