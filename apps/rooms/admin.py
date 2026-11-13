from django.contrib import admin
from .models import Amenity, RoomType, Room


@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'icon')
    list_filter = ('category',)
    search_fields = ('name',)


@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_price', 'weekend_price', 'max_guests', 'bed_type', 'size_sqft', 'is_active')
    list_filter = ('is_active', 'max_guests')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ('amenities',)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('room_number', 'room_type', 'floor', 'status', 'is_active', 'updated_at')
    list_filter = ('status', 'floor', 'room_type', 'is_active')
    search_fields = ('room_number', 'housekeeping_notes')
    list_editable = ('status',)
