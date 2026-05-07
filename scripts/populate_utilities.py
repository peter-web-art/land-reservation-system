import os
import sys
import django

# Set up Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'land_reservation.settings')
django.setup()

from lands.models import Utility

def populate():
    utilities = [
        ('Water Access', 'bi-droplet', 'Reliable water supply or connection'),
        ('Electricity', 'bi-lightning-charge', 'Connection to the power grid'),
        ('Fenced', 'bi-shield-check', 'Property is fully or partially fenced'),
        ('Road Access', 'bi-road-frontage', 'Easy access via public or private road'),
        ('Cleared Land', 'bi-tree', 'Land is cleared of heavy bush/trees'),
        ('Perimeter Wall', 'bi-bricks', 'Constructed wall around the property'),
        ('Solar Power', 'bi-sun', 'Solar panels or solar-ready infrastructure'),
        ('Fiber Internet', 'bi-router', 'High-speed internet connectivity available'),
        ('Borehole', 'bi-moisture', 'On-site borehole for water'),
        ('Street Lights', 'bi-lightbulb', 'Public street lighting available'),
    ]

    for name, icon, desc in utilities:
        obj, created = Utility.objects.get_or_create(
            name=name,
            defaults={'icon_class': icon, 'description': desc}
        )
        if created:
            print(f"Created utility: {name}")
        else:
            print(f"Utility already exists: {name}")

if __name__ == '__main__':
    print("Populating default utilities...")
    populate()
    print("Done!")
