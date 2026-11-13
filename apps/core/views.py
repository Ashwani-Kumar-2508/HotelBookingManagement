import os
from datetime import timedelta
from django.shortcuts import render
from django.utils import timezone
from django.conf import settings
from django.http import HttpResponse
from apps.rooms.models import RoomType, Amenity


def react_app_view(request):
    """Serves the modern React 18 SPA build."""
    dist_index = os.path.join(settings.BASE_DIR, 'frontend', 'dist', 'index.html')
    if os.path.exists(dist_index):
        with open(dist_index, 'r', encoding='utf-8') as f:
            return HttpResponse(f.read(), content_type='text/html')
    return home_view(request)


def home_view(request):
    """Luxury Hotel Homepage with quick reservation search widget and featured suites (SSR fallback)."""
    today = timezone.localdate()
    default_check_in = today + timedelta(days=1)
    default_check_out = default_check_in + timedelta(days=2)

    room_types = RoomType.objects.filter(is_active=True).prefetch_related('amenities')[:6]
    amenities = Amenity.objects.all()[:8]

    context = {
        'room_types': room_types,
        'amenities': amenities,
        'default_check_in': default_check_in.isoformat(),
        'default_check_out': default_check_out.isoformat(),
        'today': today.isoformat(),
    }
    return render(request, 'core/home.html', context)


def about_view(request):
    """Hotel amenities, location, and guest services guide."""
    amenities = Amenity.objects.all()
    return render(request, 'core/about.html', {'amenities': amenities})
