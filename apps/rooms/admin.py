from django.contrib import admin
from django.utils.html import format_html
from .models import Amenity, RoomType, Room


@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'icon', 'description']
    list_filter = ['category']
    search_fields = ['name']
    ordering = ['category', 'name']


@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'bed_type', 'max_guests', 'base_price', 'weekend_price', 'size_sqft', 'total_rooms_count', 'is_active']
    list_filter = ['is_active', 'bed_type']
    search_fields = ['name', 'description']
    filter_horizontal = ['amenities']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['base_price']

    fieldsets = (
        ('Identity', {'fields': ('name', 'slug', 'tagline', 'description', 'is_active')}),
        ('Capacity & Layout', {'fields': ('max_guests', 'bed_type', 'size_sqft')}),
        ('Pricing', {'fields': ('base_price', 'weekend_price')}),
        ('Amenities & Media', {'fields': ('amenities', 'image_url')}),
    )


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ['room_number', 'room_type', 'floor', 'status_badge', 'is_active', 'housekeeping_notes']
    list_filter = ['status', 'is_active', 'floor', 'room_type']
    search_fields = ['room_number', 'housekeeping_notes']
    ordering = ['floor', 'room_number']

    def status_badge(self, obj):
        colors = {
            'AVAILABLE': '#16a34a',
            'OCCUPIED': '#2563eb',
            'DIRTY': '#d97706',
            'MAINTENANCE': '#dc2626',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:4px;font-size:11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
