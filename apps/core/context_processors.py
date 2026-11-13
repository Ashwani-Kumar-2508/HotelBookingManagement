from django.conf import settings

def hotel_context(request):
    """Provides hotel settings and role flags to all templates."""
    return {
        'HOTEL': getattr(settings, 'HOTEL_SETTINGS', {}),
        'user_is_admin': request.user.is_authenticated and getattr(request.user, 'is_hotel_admin', False),
        'user_is_staff': request.user.is_authenticated and getattr(request.user, 'is_hotel_staff', False),
        'user_is_guest': request.user.is_authenticated and getattr(request.user, 'is_guest', True),
    }
