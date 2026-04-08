import json
from django.conf import settings

TANZANIA_REGIONS = [
    "Arusha", "Dar es Salaam", "Dodoma", "Geita", "Iringa",
    "Kagera", "Kaskazini Pemba", "Kaskazini Unguja", "Katavi",
    "Kigoma", "Kilimanjaro", "Kusini Pemba", "Kusini Unguja",
    "Lindi", "Manyara", "Mara", "Mbeya", "Mjini Magharibi",
    "Morogoro", "Mtwara", "Mwanza", "Njombe", "Pwani",
    "Rukwa", "Ruvuma", "Shinyanga", "Simiyu", "Singida",
    "Songwe", "Tabora", "Tanga",
]

LAND_TYPE_CHOICES = [
    ('agricultural', 'Agricultural'),
    ('residential', 'Residential'),
    ('commercial', 'Commercial'),
    ('industrial', 'Industrial'),
    ('mixed', 'Mixed Use'),
]

def global_context(request):
    from lands.models import Land, Message
    unread_messages = 0
    current_mode = 'customer'
    can_switch_mode = False

    if request.user.is_authenticated:
        try:
            unread_messages = Message.objects.filter(recipient=request.user, is_read=False).count()
        except Exception:
            unread_messages = 0
        is_admin = request.user.is_staff or getattr(request.user, 'role', None) == 'admin'
        is_owner_capable = getattr(request.user, 'role', None) == 'owner' or getattr(request.user, 'is_owner', False)
        if is_admin:
            current_mode = 'admin'
            can_switch_mode = False
        elif is_owner_capable:
            current_mode = request.session.get('current_mode', 'customer')
            if current_mode not in ('customer', 'owner'):
                current_mode = 'customer'
            can_switch_mode = True
        else:
            current_mode = 'customer'
            can_switch_mode = False

    return {
        'tanzania_regions':      TANZANIA_REGIONS,
        'tanzania_regions_json': json.dumps(TANZANIA_REGIONS),
        'total_active_lands':    0,
        'unread_messages':        unread_messages,
        'current_mode':           current_mode,
        'can_switch_mode':        can_switch_mode,
        'land_type_choices':      LAND_TYPE_CHOICES,
        'site_name':              getattr(settings, 'SITE_NAME', 'LandReserve'),
        'support_email':          getattr(settings, 'SUPPORT_EMAIL', 'support@landreserve.co.tz'),
    }
