from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from lands.views import land_list


def health_check(request):
    """Health check endpoint for uptime monitoring and load balancers."""
    from django.db import connection
    try:
        connection.ensure_connection()
        db_status = 'ok'
    except Exception:
        db_status = 'error'
    return JsonResponse({
        'status': 'ok' if db_status == 'ok' else 'degraded',
        'database': db_status,
    })


urlpatterns = [
    path('', land_list),
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health_check'),       # Health check endpoint
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/', include('accounts.urls')),
    path('accounts/', include('allauth.urls')),
    path('lands/', include('lands.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
