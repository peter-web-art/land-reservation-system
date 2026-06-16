from django.core.management.base import BaseCommand
from lands.models import Reservation


class Command(BaseCommand):
    help = 'Backfill Reservation.payment_method from latest PaymentRecord where missing.'

    def handle(self, *args, **options):
        qs = Reservation.objects.filter(payment_method__isnull=True).prefetch_related('payments')
        total = qs.count()
        updated = 0
        for r in qs:
            latest = r.payments.order_by('-created_on').first()
            if latest and latest.payment_method:
                r.payment_method = latest.payment_method
                r.save(update_fields=['payment_method', 'updated_on'])
                updated += 1

        self.stdout.write(self.style.SUCCESS(f'Processed {total} reservations; updated {updated}'))
