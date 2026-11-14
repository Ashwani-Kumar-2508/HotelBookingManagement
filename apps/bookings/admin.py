from django.contrib import admin
from django.utils.html import format_html
from .models import BookingHold, Reservation, BookingAuditLog


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = [
        'booking_reference', 'guest_name', 'room_number_display',
        'check_in', 'check_out', 'num_nights', 'status_badge',
        'payment_status', 'total_amount', 'created_at',
    ]
    list_filter = ['status', 'payment_status', 'check_in', 'room_type']
    search_fields = ['booking_reference', 'guest_name', 'guest_email', 'guest_phone']
    readonly_fields = [
        'booking_reference', 'created_at', 'updated_at',
        'checked_in_at', 'checked_out_at', 'cancelled_at', 'transaction_id',
    ]
    ordering = ['-created_at']
    list_per_page = 25
    date_hierarchy = 'check_in'

    fieldsets = (
        ('Booking Reference', {
            'fields': ('booking_reference', 'status', 'payment_status')
        }),
        ('Guest Details', {
            'fields': ('guest', 'guest_name', 'guest_email', 'guest_phone', 'special_requests')
        }),
        ('Stay Details', {
            'fields': ('room', 'room_type', 'check_in', 'check_out', 'guests_count', 'num_nights')
        }),
        ('Financial Breakdown', {
            'fields': (
                'nightly_rate', 'room_subtotal', 'addons_amount',
                'tax_amount', 'service_fee', 'total_amount'
            )
        }),
        ('Payment', {
            'fields': ('payment_method', 'transaction_id', 'paid_at')
        }),
        ('Lifecycle Timestamps', {
            'fields': ('created_at', 'updated_at', 'checked_in_at', 'checked_out_at', 'cancelled_at', 'cancellation_reason'),
            'classes': ('collapse',)
        }),
    )

    def room_number_display(self, obj):
        return f"Room {obj.room.room_number}"
    room_number_display.short_description = 'Room'

    def status_badge(self, obj):
        colors = {
            'CONFIRMED': '#2563eb',
            'CHECKED_IN': '#16a34a',
            'CHECKED_OUT': '#6b7280',
            'CANCELLED': '#dc2626',
            'NO_SHOW': '#d97706',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:4px;font-size:11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'


@admin.register(BookingHold)
class BookingHoldAdmin(admin.ModelAdmin):
    list_display = ['hold_id', 'room', 'guest', 'check_in', 'check_out', 'is_consumed', 'expires_at', 'created_at']
    list_filter = ['is_consumed', 'check_in']
    search_fields = ['hold_id__iexact', 'room__room_number', 'guest__email']
    readonly_fields = ['hold_id', 'created_at', 'expires_at']
    ordering = ['-created_at']


@admin.register(BookingAuditLog)
class BookingAuditLogAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'action', 'title', 'user_display', 'room', 'booking_ref_display']
    list_filter = ['action', 'created_at']
    search_fields = ['title', 'details', 'user__email', 'reservation__booking_reference']
    readonly_fields = ['reservation', 'room', 'user', 'action', 'title', 'details', 'ip_address', 'created_at']
    ordering = ['-created_at']

    def has_add_permission(self, request):
        return False  # Audit logs are immutable

    def has_change_permission(self, request, obj=None):
        return False  # Audit logs are immutable

    def user_display(self, obj):
        return obj.user.email if obj.user else '—'
    user_display.short_description = 'Actor'

    def booking_ref_display(self, obj):
        return obj.reservation.booking_reference if obj.reservation else '—'
    booking_ref_display.short_description = 'Booking Ref'
