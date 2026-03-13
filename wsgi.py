import os
import sys

# Add your project directory to the sys.path
project_dir = os.path.dirname(__file__)
sys.path.insert(0, project_dir)

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'land_reservation.settings')

# Setup Django
import django
django.setup()

# Import the WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()