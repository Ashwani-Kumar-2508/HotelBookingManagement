from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    # OpenAPI & Swagger UI
    path('docs/', views.swagger_docs_view, name='docs'),
    path('openapi.json', views.openapi_spec_view, name='openapi_spec'),

    # RESTful API Endpoints
    path('v1/rooms/', views.api_rooms_list, name='rooms_list'),
    path('v1/availability/', views.api_availability, name='availability'),
    path('v1/holds/', views.api_create_hold, name='create_hold'),
    path('v1/bookings/', views.api_confirm_booking, name='confirm_booking'),
    path('v1/bookings/<str:reference>/', views.api_booking_detail, name='booking_detail'),
    path('v1/bookings/<str:reference>/cancel/', views.api_cancel_booking, name='cancel_booking'),
    path('v1/bookings/<str:reference>/check-in/', views.api_check_in, name='check_in'),
    path('v1/bookings/<str:reference>/check-out/', views.api_check_out, name='check_out'),
    path('v1/reports/operations/', views.api_operations_report, name='operations_report'),
]
