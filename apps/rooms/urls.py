from django.urls import path
from . import views

app_name = 'rooms'

urlpatterns = [
    path('types/', views.room_type_list, name='room_type_list'),
    path('types/create/', views.room_type_create, name='room_type_create'),
    path('types/<int:pk>/edit/', views.room_type_edit, name='room_type_edit'),
    path('inventory/', views.room_inventory_list, name='room_inventory'),
    path('inventory/create/', views.room_create, name='room_create'),
    path('rooms/<int:pk>/status/', views.update_room_status, name='update_room_status'),
]
