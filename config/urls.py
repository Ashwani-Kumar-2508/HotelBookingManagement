"""
URL configuration for GrandView Hotel Management & Reservation System.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('rooms/', include('apps.rooms.urls', namespace='rooms')),
    path('bookings/', include('apps.bookings.urls', namespace='bookings')),
    path('reports/', include('apps.reports.urls', namespace='reports')),
    path('api/', include('apps.api.urls', namespace='api')),
    path('', include('apps.core.urls', namespace='core')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
