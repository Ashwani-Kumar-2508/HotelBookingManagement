from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages


def hotel_admin_required(view_func):
    """
    Decorator for views that checks if the logged-in user is an Administrator.
    Rejects unauthorized access with HTTP 403 PermissionDenied.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Please log in to access this page.")
            return redirect(f"/accounts/login/?next={request.path}")
        if not request.user.is_hotel_admin:
            raise PermissionDenied("Access Denied: Hotel Administrator privileges required.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def hotel_staff_required(view_func):
    """
    Decorator for views that checks if the logged-in user is Hotel Staff or Admin.
    Rejects unauthorized access with HTTP 403 PermissionDenied.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Please log in with staff credentials.")
            return redirect(f"/accounts/login/?next={request.path}")
        if not request.user.is_hotel_staff:
            raise PermissionDenied("Access Denied: Front Desk / Staff privileges required.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view
