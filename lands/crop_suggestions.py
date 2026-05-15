"""
Auto Crop Suggestion Engine for Tanzania
=========================================
Recommends suitable crops based on:
  - Geographical location (Tanzania region)
  - Soil fertility level
  - Topography
  - Land use type
"""

# ── Tanzania Region → Agro-Ecological Zone mapping ──────────────────────────
# Each region is mapped to its dominant climate/zone characteristics
REGION_PROFILES = {
    'dar_es_salaam': {
        'zone': 'coastal_lowland',
        'rainfall': 'high',
        'temperature': 'hot',
        'altitude': 'low',
    },
    'pwani': {
        'zone': 'coastal_lowland',
        'rainfall': 'high',
        'temperature': 'hot',
        'altitude': 'low',
    },
    'tanga': {
        'zone': 'coastal_lowland',
        'rainfall': 'high',
        'temperature': 'hot',
        'altitude': 'low',
    },
    'lindi': {
        'zone': 'coastal_lowland',
        'rainfall': 'moderate',
        'temperature': 'hot',
        'altitude': 'low',
    },
    'mtwara': {
        'zone': 'coastal_lowland',
        'rainfall': 'moderate',
        'temperature': 'hot',
        'altitude': 'low',
    },
    'morogoro': {
        'zone': 'eastern_plateau',
        'rainfall': 'moderate',
        'temperature': 'warm',
        'altitude': 'medium',
    },
    'dodoma': {
        'zone': 'central_plateau',
        'rainfall': 'low',
        'temperature': 'warm',
        'altitude': 'medium',
    },
    'singida': {
        'zone': 'central_plateau',
        'rainfall': 'low',
        'temperature': 'warm',
        'altitude': 'medium',
    },
    'tabora': {
        'zone': 'western_plateau',
        'rainfall': 'moderate',
        'temperature': 'warm',
        'altitude': 'medium',
    },
    'shinyanga': {
        'zone': 'lake_zone',
        'rainfall': 'moderate',
        'temperature': 'warm',
        'altitude': 'medium',
    },
    'mwanza': {
        'zone': 'lake_zone',
        'rainfall': 'moderate',
        'temperature': 'warm',
        'altitude': 'medium',
    },
    'mara': {
        'zone': 'lake_zone',
        'rainfall': 'moderate',
        'temperature': 'warm',
        'altitude': 'medium',
    },
    'simiyu': {
        'zone': 'lake_zone',
        'rainfall': 'moderate',
        'temperature': 'warm',
        'altitude': 'medium',
    },
    'geita': {
        'zone': 'lake_zone',
        'rainfall': 'moderate',
        'temperature': 'warm',
        'altitude': 'medium',
    },
    'kagera': {
        'zone': 'lake_zone',
        'rainfall': 'high',
        'temperature': 'warm',
        'altitude': 'medium',
    },
    'kigoma': {
        'zone': 'western_rift',
        'rainfall': 'high',
        'temperature': 'warm',
        'altitude': 'medium',
    },
    'katavi': {
        'zone': 'western_rift',
        'rainfall': 'moderate',
        'temperature': 'warm',
        'altitude': 'medium',
    },
    'rukwa': {
        'zone': 'southern_highlands',
        'rainfall': 'moderate',
        'temperature': 'cool',
        'altitude': 'high',
    },
    'mbeya': {
        'zone': 'southern_highlands',
        'rainfall': 'high',
        'temperature': 'cool',
        'altitude': 'high',
    },
    'songwe': {
        'zone': 'southern_highlands',
        'rainfall': 'high',
        'temperature': 'cool',
        'altitude': 'high',
    },
    'iringa': {
        'zone': 'southern_highlands',
        'rainfall': 'moderate',
        'temperature': 'cool',
        'altitude': 'high',
    },
    'njombe': {
        'zone': 'southern_highlands',
        'rainfall': 'high',
        'temperature': 'cool',
        'altitude': 'high',
    },
    'ruvuma': {
        'zone': 'southern_lowland',
        'rainfall': 'high',
        'temperature': 'warm',
        'altitude': 'medium',
    },
    'arusha': {
        'zone': 'northern_highlands',
        'rainfall': 'moderate',
        'temperature': 'cool',
        'altitude': 'high',
    },
    'kilimanjaro': {
        'zone': 'northern_highlands',
        'rainfall': 'high',
        'temperature': 'cool',
        'altitude': 'high',
    },
    'manyara': {
        'zone': 'northern_highlands',
        'rainfall': 'moderate',
        'temperature': 'warm',
        'altitude': 'medium',
    },
}

# ── Crop Database ────────────────────────────────────────────────────────────
# Each crop has its requirements and metadata for display
CROP_DATABASE = {
    'maize': {
        'name': 'Maize (Corn)',
        'icon': '🌽',
        'season': 'March – July',
        'water_need': 'moderate',
        'min_fertility': 'moderate',
        'suited_zones': ['lake_zone', 'southern_highlands', 'northern_highlands', 'eastern_plateau', 'western_plateau', 'central_plateau'],
        'suited_topography': ['flat', 'rolling', 'sloped'],
        'temperature': ['warm', 'cool'],
        'description': 'Staple food crop thriving in well-drained soils with moderate rainfall. Excellent for commercial farming.',
        'yield_potential': 'High',
        'market_demand': 'Very High',
    },
    'rice': {
        'name': 'Rice (Paddy)',
        'icon': '🌾',
        'season': 'November – April',
        'water_need': 'high',
        'min_fertility': 'high',
        'suited_zones': ['coastal_lowland', 'eastern_plateau', 'lake_zone', 'western_rift'],
        'suited_topography': ['flat', 'depressed'],
        'temperature': ['hot', 'warm'],
        'description': 'Requires flooded or well-irrigated flat land. Major cash crop in Morogoro, Mbeya, and Shinyanga.',
        'yield_potential': 'High',
        'market_demand': 'Very High',
    },
    'cassava': {
        'name': 'Cassava',
        'icon': '🥔',
        'season': 'Year-round planting',
        'water_need': 'low',
        'min_fertility': 'low',
        'suited_zones': ['coastal_lowland', 'lake_zone', 'eastern_plateau', 'western_plateau', 'southern_lowland', 'western_rift'],
        'suited_topography': ['flat', 'rolling', 'sloped'],
        'temperature': ['hot', 'warm'],
        'description': 'Drought-tolerant root crop that grows well even in poor soils. Important food security crop.',
        'yield_potential': 'Moderate',
        'market_demand': 'High',
    },
    'coffee': {
        'name': 'Coffee (Arabica/Robusta)',
        'icon': '☕',
        'season': 'Perennial — harvest May–Oct',
        'water_need': 'moderate',
        'min_fertility': 'high',
        'suited_zones': ['northern_highlands', 'southern_highlands', 'lake_zone'],
        'suited_topography': ['sloped', 'rolling', 'mountainous'],
        'temperature': ['cool'],
        'description': 'Premium export crop. Arabica thrives above 1,200m in Kilimanjaro & Mbeya. Robusta suits lower altitudes in Kagera.',
        'yield_potential': 'Moderate',
        'market_demand': 'Very High (Export)',
    },
    'tea': {
        'name': 'Tea',
        'icon': '🍵',
        'season': 'Perennial — year-round harvest',
        'water_need': 'high',
        'min_fertility': 'high',
        'suited_zones': ['southern_highlands', 'northern_highlands'],
        'suited_topography': ['sloped', 'rolling', 'mountainous'],
        'temperature': ['cool'],
        'description': 'Requires high altitude (1,500m+), acidic soils, and reliable rainfall. Major crop in Iringa, Njombe & Mufindi.',
        'yield_potential': 'Moderate',
        'market_demand': 'High (Export)',
    },
    'banana': {
        'name': 'Banana / Plantain',
        'icon': '🍌',
        'season': 'Perennial — year-round',
        'water_need': 'high',
        'min_fertility': 'high',
        'suited_zones': ['northern_highlands', 'lake_zone', 'coastal_lowland', 'southern_highlands'],
        'suited_topography': ['flat', 'rolling', 'sloped'],
        'temperature': ['warm', 'cool'],
        'description': 'Requires deep fertile soils and reliable moisture. Dominant in Kagera, Kilimanjaro, and Mbeya.',
        'yield_potential': 'High',
        'market_demand': 'High',
    },
    'sunflower': {
        'name': 'Sunflower',
        'icon': '🌻',
        'season': 'February – June',
        'water_need': 'low',
        'min_fertility': 'moderate',
        'suited_zones': ['central_plateau', 'southern_highlands', 'eastern_plateau', 'western_plateau'],
        'suited_topography': ['flat', 'rolling'],
        'temperature': ['warm', 'cool'],
        'description': 'Drought-tolerant oilseed crop. Excellent for Dodoma and Singida regions. Growing commercial demand for cooking oil.',
        'yield_potential': 'Moderate',
        'market_demand': 'High',
    },
    'cotton': {
        'name': 'Cotton',
        'icon': '🏵️',
        'season': 'November – March',
        'water_need': 'moderate',
        'min_fertility': 'moderate',
        'suited_zones': ['lake_zone', 'western_plateau', 'central_plateau'],
        'suited_topography': ['flat', 'rolling'],
        'temperature': ['warm', 'hot'],
        'description': 'Major cash crop in the Lake Zone. Requires warm temperatures and well-drained soils.',
        'yield_potential': 'Moderate',
        'market_demand': 'High (Export)',
    },
    'beans': {
        'name': 'Common Beans',
        'icon': '🫘',
        'season': 'March – June / Oct – Dec',
        'water_need': 'moderate',
        'min_fertility': 'moderate',
        'suited_zones': ['southern_highlands', 'northern_highlands', 'lake_zone', 'eastern_plateau'],
        'suited_topography': ['flat', 'rolling', 'sloped'],
        'temperature': ['cool', 'warm'],
        'description': 'Important protein source and nitrogen fixer. Grows well in rotation with maize.',
        'yield_potential': 'Moderate',
        'market_demand': 'Very High',
    },
    'cashew': {
        'name': 'Cashew Nuts',
        'icon': '🥜',
        'season': 'Perennial — harvest Oct–Jan',
        'water_need': 'low',
        'min_fertility': 'low',
        'suited_zones': ['coastal_lowland', 'southern_lowland'],
        'suited_topography': ['flat', 'rolling'],
        'temperature': ['hot'],
        'description': 'Tanzania is a major cashew exporter. Thrives in coastal sandy soils of Mtwara, Lindi and Pwani.',
        'yield_potential': 'High',
        'market_demand': 'Very High (Export)',
    },
    'coconut': {
        'name': 'Coconut',
        'icon': '🥥',
        'season': 'Perennial — year-round',
        'water_need': 'moderate',
        'min_fertility': 'moderate',
        'suited_zones': ['coastal_lowland'],
        'suited_topography': ['flat', 'rolling'],
        'temperature': ['hot'],
        'description': 'Thrives in coastal regions with sandy soils. Multi-purpose crop (oil, fibre, food).',
        'yield_potential': 'Moderate',
        'market_demand': 'Moderate',
    },
    'sisal': {
        'name': 'Sisal',
        'icon': '🌿',
        'season': 'Perennial — harvest every 2–3 yrs',
        'water_need': 'low',
        'min_fertility': 'low',
        'suited_zones': ['coastal_lowland', 'eastern_plateau', 'northern_highlands'],
        'suited_topography': ['flat', 'rolling'],
        'temperature': ['hot', 'warm'],
        'description': 'Hardy fibre crop requiring minimal water. Tanzania was once the world\'s largest producer.',
        'yield_potential': 'Low',
        'market_demand': 'Moderate (Export)',
    },
    'tobacco': {
        'name': 'Tobacco',
        'icon': '🍂',
        'season': 'September – February',
        'water_need': 'moderate',
        'min_fertility': 'high',
        'suited_zones': ['western_plateau', 'southern_highlands', 'central_plateau'],
        'suited_topography': ['flat', 'rolling'],
        'temperature': ['warm'],
        'description': 'Major cash crop in Tabora and surrounding regions. Requires fertile, well-drained soils.',
        'yield_potential': 'Moderate',
        'market_demand': 'High (Export)',
    },
    'sorghum': {
        'name': 'Sorghum',
        'icon': '🌾',
        'season': 'February – June',
        'water_need': 'low',
        'min_fertility': 'low',
        'suited_zones': ['central_plateau', 'lake_zone', 'eastern_plateau'],
        'suited_topography': ['flat', 'rolling'],
        'temperature': ['warm', 'hot'],
        'description': 'Drought-resistant cereal suited for semi-arid areas. Growing demand for brewing and food.',
        'yield_potential': 'Moderate',
        'market_demand': 'Moderate',
    },
    'sweet_potato': {
        'name': 'Sweet Potato',
        'icon': '🍠',
        'season': 'Year-round (rain-fed)',
        'water_need': 'moderate',
        'min_fertility': 'moderate',
        'suited_zones': ['lake_zone', 'eastern_plateau', 'southern_highlands', 'coastal_lowland', 'western_rift'],
        'suited_topography': ['flat', 'rolling', 'sloped'],
        'temperature': ['warm', 'hot'],
        'description': 'Versatile root crop with orange-flesh varieties rich in Vitamin A. Short maturation period.',
        'yield_potential': 'High',
        'market_demand': 'High',
    },
    'groundnut': {
        'name': 'Groundnut (Peanut)',
        'icon': '🥜',
        'season': 'December – April',
        'water_need': 'moderate',
        'min_fertility': 'moderate',
        'suited_zones': ['central_plateau', 'western_plateau', 'eastern_plateau', 'lake_zone'],
        'suited_topography': ['flat', 'rolling'],
        'temperature': ['warm', 'hot'],
        'description': 'Nitrogen-fixing legume excellent for crop rotation. Important protein and oil source.',
        'yield_potential': 'Moderate',
        'market_demand': 'High',
    },
    'tomato': {
        'name': 'Tomatoes',
        'icon': '🍅',
        'season': 'Year-round (irrigated)',
        'water_need': 'high',
        'min_fertility': 'high',
        'suited_zones': ['northern_highlands', 'eastern_plateau', 'southern_highlands', 'coastal_lowland'],
        'suited_topography': ['flat', 'rolling'],
        'temperature': ['warm', 'cool'],
        'description': 'High-value vegetable crop with strong domestic market demand. Requires good irrigation.',
        'yield_potential': 'Very High',
        'market_demand': 'Very High',
    },
    'avocado': {
        'name': 'Avocado',
        'icon': '🥑',
        'season': 'Perennial — harvest Mar–Jul',
        'water_need': 'moderate',
        'min_fertility': 'high',
        'suited_zones': ['northern_highlands', 'southern_highlands'],
        'suited_topography': ['sloped', 'rolling'],
        'temperature': ['cool'],
        'description': 'Fast-growing export market. Hass variety thriving in highland areas of Njombe, Iringa, and Mbeya.',
        'yield_potential': 'High',
        'market_demand': 'Very High (Export)',
    },
    'clove': {
        'name': 'Cloves',
        'icon': '🌺',
        'season': 'Perennial — harvest Sep–Jan',
        'water_need': 'high',
        'min_fertility': 'high',
        'suited_zones': ['coastal_lowland'],
        'suited_topography': ['flat', 'rolling'],
        'temperature': ['hot'],
        'description': 'Zanzibar specialty spice with high export value. Suited for humid tropical climates.',
        'yield_potential': 'Low',
        'market_demand': 'High (Export)',
    },
    'onion': {
        'name': 'Onions',
        'icon': '🧅',
        'season': 'May – October (dry season)',
        'water_need': 'moderate',
        'min_fertility': 'moderate',
        'suited_zones': ['northern_highlands', 'central_plateau', 'lake_zone'],
        'suited_topography': ['flat'],
        'temperature': ['warm', 'cool'],
        'description': 'High-demand vegetable crop grown extensively in Arusha, Dodoma, and Singida. Requires well-drained soils.',
        'yield_potential': 'High',
        'market_demand': 'Very High',
    },
}

# ── Fertility level ordering ────────────────────────────────────────────────
FERTILITY_LEVELS = {
    'very_low': 0,
    'low': 1,
    'moderate': 2,
    'high': 3,
    'very_high': 4,
}

FERTILITY_MIN_MAP = {
    'low': 1,
    'moderate': 2,
    'high': 3,
}


def _extract_region(location_str):
    """
    Try to identify a Tanzania region from a free-text location string.
    Falls back to free-text matching if structured region key is not provided.
    """
    if not location_str:
        return None
    # Direct match (structured region key like 'dar_es_salaam')
    if location_str in REGION_PROFILES:
        return location_str
    # Fallback: free-text search
    location_lower = location_str.lower().replace('_', ' ')
    for region_key in REGION_PROFILES:
        if region_key.replace('_', ' ') in location_lower:
            return region_key
    return None


def _fertility_score(level_str):
    """Convert a fertility level string to a numeric score."""
    return FERTILITY_LEVELS.get(level_str, 2)  # default to moderate


def get_crop_suggestions(location, soil_fertility='moderate', topography='flat', land_use='agricultural', region_key=None):
    """
    Main suggestion engine.
    Returns a list of crop suggestion dicts sorted by suitability score.

    Parameters
    ----------
    location : str
        Free-text location OR structured region key (e.g. 'mbeya')
    soil_fertility : str
        One of: very_low, low, moderate, high, very_high
    topography : str
        One of: flat, sloped, rolling, mountainous, depressed
    land_use : str
        One of: agricultural, residential, commercial, industrial, mixed
    region_key : str, optional
        Direct region key from the structured model field. Takes precedence.
    """
    # Only suggest crops for agricultural or mixed-use land
    if land_use not in ('agricultural', 'mixed'):
        return []

    # Use direct region_key if provided, otherwise extract from location
    if not region_key:
        region_key = _extract_region(location)
    region_profile = REGION_PROFILES.get(region_key, {})
    zone = region_profile.get('zone', 'central_plateau')
    temp = region_profile.get('temperature', 'warm')
    fertility = _fertility_score(soil_fertility)

    suggestions = []

    for crop_key, crop in CROP_DATABASE.items():
        score = 0
        reasons = []

        # Zone match (most important)
        if zone in crop['suited_zones']:
            score += 35
            reasons.append(f"Well-suited to {region_key.replace('_', ' ').title() if region_key else 'this'} region")
        else:
            # Partial match — still show but lower score
            score += 5

        # Temperature match
        if temp in crop['temperature']:
            score += 20
            reasons.append(f"Thrives in {temp} temperatures")
        elif not region_profile:
            # No region data, neutral score
            score += 10

        # Topography match
        if topography in crop['suited_topography']:
            score += 15
            reasons.append(f"Suitable for {topography} terrain")
        else:
            score -= 10

        # Soil fertility check
        crop_min = FERTILITY_MIN_MAP.get(crop['min_fertility'], 2)
        if fertility >= crop_min:
            score += 20
            if fertility >= crop_min + 1:
                reasons.append("Excellent soil fertility for this crop")
            else:
                reasons.append("Adequate soil fertility")
        else:
            deficit = crop_min - fertility
            score -= deficit * 15
            reasons.append("May need soil amendment / fertiliser")

        # Market demand bonus
        if 'Very High' in crop.get('market_demand', ''):
            score += 10
            reasons.append("Very high market demand")
        elif 'High' in crop.get('market_demand', ''):
            score += 5

        # Only include crops with a reasonable suitability
        if score >= 30:
            suggestions.append({
                'key': crop_key,
                'name': crop['name'],
                'icon': crop['icon'],
                'season': crop['season'],
                'description': crop['description'],
                'yield_potential': crop['yield_potential'],
                'market_demand': crop['market_demand'],
                'score': min(score, 100),  # Cap at 100
                'reasons': reasons[:3],  # Limit reasons
                'suitability': (
                    'Excellent' if score >= 80 else
                    'Good' if score >= 60 else
                    'Moderate' if score >= 40 else
                    'Low'
                ),
                'suitability_color': (
                    'green' if score >= 80 else
                    'blue' if score >= 60 else
                    'amber' if score >= 40 else
                    'gray'
                ),
            })

    # Sort by score descending
    suggestions.sort(key=lambda x: x['score'], reverse=True)

    # Return top 8
    return suggestions[:8]
