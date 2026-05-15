"""
Tanzania Administrative Divisions Data
=======================================
Cascading location data: Region → District → Ward (text) → Street (text)
Covers all 26 mainland Tanzania regions and their districts.
"""

# Region choices for model field
REGION_CHOICES = [
    ('arusha', 'Arusha'),
    ('dar_es_salaam', 'Dar es Salaam'),
    ('dodoma', 'Dodoma'),
    ('geita', 'Geita'),
    ('iringa', 'Iringa'),
    ('kagera', 'Kagera'),
    ('katavi', 'Katavi'),
    ('kigoma', 'Kigoma'),
    ('kilimanjaro', 'Kilimanjaro'),
    ('lindi', 'Lindi'),
    ('manyara', 'Manyara'),
    ('mara', 'Mara'),
    ('mbeya', 'Mbeya'),
    ('morogoro', 'Morogoro'),
    ('mtwara', 'Mtwara'),
    ('mwanza', 'Mwanza'),
    ('njombe', 'Njombe'),
    ('pwani', 'Pwani'),
    ('rukwa', 'Rukwa'),
    ('ruvuma', 'Ruvuma'),
    ('shinyanga', 'Shinyanga'),
    ('simiyu', 'Simiyu'),
    ('singida', 'Singida'),
    ('songwe', 'Songwe'),
    ('tabora', 'Tabora'),
    ('tanga', 'Tanga'),
]

# Region → Districts mapping
REGION_DISTRICTS = {
    'arusha': [
        'Arusha City', 'Arusha', 'Karatu', 'Longido', 'Meru', 'Monduli', 'Ngorongoro',
    ],
    'dar_es_salaam': [
        'Ilala', 'Kinondoni', 'Temeke', 'Ubungo', 'Kigamboni',
    ],
    'dodoma': [
        'Dodoma City', 'Bahi', 'Chamwino', 'Chemba', 'Kondoa', 'Kongwa', 'Mpwapwa',
    ],
    'geita': [
        'Geita', 'Bukombe', 'Chato', 'Mbogwe', "Nyang'hwale",
    ],
    'iringa': [
        'Iringa Municipal', 'Iringa', 'Kilolo', 'Mufindi',
    ],
    'kagera': [
        'Bukoba Municipal', 'Bukoba', 'Biharamulo', 'Karagwe', 'Kyerwa',
        'Missenyi', 'Muleba', 'Ngara',
    ],
    'katavi': [
        'Mpanda Municipal', 'Mpanda', 'Mlele',
    ],
    'kigoma': [
        'Kigoma-Ujiji', 'Kigoma', 'Kasulu', 'Kasulu Town', 'Kakonko',
        'Kibondo', 'Uvinza', 'Buhigwe',
    ],
    'kilimanjaro': [
        'Moshi Municipal', 'Moshi', 'Hai', 'Mwanga', 'Rombo', 'Same', 'Siha',
    ],
    'lindi': [
        'Lindi Municipal', 'Lindi', 'Kilwa', 'Liwale', 'Nachingwea', 'Ruangwa',
    ],
    'manyara': [
        'Babati Town', 'Babati', 'Hanang', 'Kiteto', 'Mbulu', 'Simanjiro',
    ],
    'mara': [
        'Musoma Municipal', 'Musoma', 'Bunda', 'Butiama', 'Rorya',
        'Serengeti', 'Tarime',
    ],
    'mbeya': [
        'Mbeya City', 'Mbeya', 'Busokelo', 'Chunya', 'Mbarali', 'Rungwe',
    ],
    'morogoro': [
        'Morogoro Municipal', 'Morogoro', 'Gairo', 'Kilombero', 'Kilosa',
        'Malinyi', 'Mvomero', 'Ulanga', 'Ifakara Town',
    ],
    'mtwara': [
        'Mtwara Municipal', 'Mtwara', 'Masasi', 'Masasi Town',
        'Nanyumbu', 'Newala', 'Tandahimba',
    ],
    'mwanza': [
        'Nyamagana', 'Ilemela', 'Kwimba', 'Magu', 'Misungwi',
        'Sengerema', 'Ukerewe',
    ],
    'njombe': [
        'Njombe Town', 'Njombe', 'Ludewa', 'Makambako Town',
        'Makete', "Wanging'ombe",
    ],
    'pwani': [
        'Kibaha Town', 'Kibaha', 'Bagamoyo', 'Kisarawe',
        'Mafia', 'Mkuranga', 'Rufiji',
    ],
    'rukwa': [
        'Sumbawanga Municipal', 'Sumbawanga', 'Kalambo', 'Nkasi',
    ],
    'ruvuma': [
        'Songea Municipal', 'Songea', 'Mbinga', 'Mbinga Town',
        'Namtumbo', 'Nyasa', 'Tunduru',
    ],
    'shinyanga': [
        'Shinyanga Municipal', 'Shinyanga', 'Kahama', 'Kahama Town',
        'Kishapu', 'Ushetu',
    ],
    'simiyu': [
        'Bariadi', 'Bariadi Town', 'Busega', 'Itilima', 'Maswa', 'Meatu',
    ],
    'singida': [
        'Singida Municipal', 'Singida', 'Ikungi', 'Iramba', 'Manyoni', 'Mkalama',
    ],
    'songwe': [
        'Tunduma Town', 'Mbozi', 'Momba', 'Songwe',
    ],
    'tabora': [
        'Tabora Municipal', 'Tabora', 'Igunga', 'Kaliua',
        'Nzega', 'Nzega Town', 'Sikonge', 'Urambo', 'Uyui',
    ],
    'tanga': [
        'Tanga City', 'Handeni', 'Handeni Town', 'Kilindi',
        'Korogwe', 'Korogwe Town', 'Lushoto', 'Mkinga', 'Muheza', 'Pangani',
    ],
}


def get_region_display(region_key):
    """Get the display name for a region key."""
    for key, name in REGION_CHOICES:
        if key == region_key:
            return name
    return region_key.replace('_', ' ').title() if region_key else ''


def get_districts_for_region(region_key):
    """Return list of districts for a given region key."""
    return REGION_DISTRICTS.get(region_key, [])


def build_full_location(region, district, ward, street):
    """Build a human-readable location string from components."""
    parts = []
    if street:
        parts.append(street)
    if ward:
        parts.append(ward)
    if district:
        parts.append(district)
    if region:
        parts.append(get_region_display(region))
    return ', '.join(parts) if parts else ''
