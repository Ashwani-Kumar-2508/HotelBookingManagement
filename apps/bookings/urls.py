from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    path('search/', views.search_rooms, name='search'),
    path('room/<slug:slug>/', views.room_detail, name='room_detail'),
    path('hold/', views.create_hold, name='create_hold'),
    path('checkout/<uuid:hold_id>/', views.checkout_view, name='checkout'),
    path('confirmation/<str:reference>/', views.booking_confirmation, name='confirmation'),
    path('my-bookings/', views.guest_bookings_list, name='guest_bookings'),
    path('cancel/<str:reference>/', views.guest_cancel_booking, name='cancel'),
    
    # Staff / Admin endpoints
    path('staff/desk/', views.staff_desk_view, name='staff_desk'),
    path('staff/check-in/<str:reference>/', views.staff_check_in, name='staff_check_in'),
    path('staff/check-out/<str:reference>/', views.staff_check_out, name='staff_check_out'),
    path('admin/audit-trail/', views.audit_trail_view, name='audit_trail'),
]
