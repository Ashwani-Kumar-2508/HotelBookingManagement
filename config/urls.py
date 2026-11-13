"""
URL configuration for GrandView Hotel Management & Reservation System.
"""
import os
from django.contrib import admin
from django.urls import path, re_path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('rooms/', include('apps.rooms.urls', namespace='rooms')),
    path('bookings/', include('apps.bookings.urls', namespace='bookings')),
    path('reports/', include('apps.reports.urls', namespace='reports')),
    path('api/', include('apps.api.urls', namespace='api')),

    # Serve Vite React build assets
    re_path(r'^assets/(?P<path>.*)$', serve, {
        'document_root': os.path.join(settings.BASE_DIR, 'frontend', 'dist', 'assets')
    }),

    path('', include('apps.core.urls', namespace='core')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
