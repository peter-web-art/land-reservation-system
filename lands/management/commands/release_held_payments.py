from django.core.management.base import BaseCommand
from lands.services import release_matured_escrow_payments

class Command(BaseCommand):
    help = 'Release confirmed payments after 24 hours by marking owner_received_on and notifying owner/admins'

    def handle(self, *args, **options):
        payments = release_matured_escrow_payments()
        if not payments:
            self.stdout.write('No payments eligible for automatic release.')
            return

        for p in payments:
            self.stdout.write(f'Released payment {p.id} ({p.payment_reference}) to {p.reservation.land.owner.username}')
