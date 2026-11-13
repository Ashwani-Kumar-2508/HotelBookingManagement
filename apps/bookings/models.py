import uuid
from django.db import models
from django.db.models import Q, F
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.rooms.models import Room, RoomType


class BookingHold(models.Model):
    """
    Temporary inventory hold to prevent double-booking race conditions while 
    a guest reviews itemized pricing and enters payment details.
    Expired holds automatically cease blocking availability.
    """
    hold_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='holds')
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE, related_name='holds')
    guest = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    check_in = models.DateField(db_index=True)
    check_out = models.DateField(db_index=True)
    guests_count = models.PositiveIntegerField(default=1)
    estimated_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    is_consumed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['room', 'check_in', 'check_out', 'expires_at', 'is_consumed']),
        ]

    def __str__(self):
        status_text = "EXPIRED" if self.is_expired else ("CONSUMED" if self.is_consumed else "ACTIVE")
        return f"Hold {self.hold_id} for Room {self.room.room_number} [{status_text}]"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_active(self):
        return (not self.is_consumed) and (timezone.now() <= self.expires_at)

    @property
    def remaining_seconds(self):
        if self.is_expired:
            return 0
        diff = self.expires_at - timezone.now()
        return max(0, int(diff.total_seconds()))


class Reservation(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = 'CONFIRMED', _('Confirmed / Guaranteed')
        CHECKED_IN = 'CHECKED_IN', _('Checked In (In-House)')
        CHECKED_OUT = 'CHECKED_OUT', _('Checked Out (Departed)')
        CANCELLED = 'CANCELLED', _('Cancelled')
        NO_SHOW = 'NO_SHOW', _('No Show')

    class PaymentStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        PAID = 'PAID', _('Paid in Full')
        REFUNDED = 'REFUNDED', _('Refunded')

    booking_reference = models.CharField(max_length=24, unique=True, db_index=True)
    guest = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='reservations')
    guest_name = models.CharField(max_length=150)
    guest_email = models.EmailField()
    guest_phone = models.CharField(max_length=30)
    special_requests = models.TextField(blank=True, default='')

    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name='reservations')
    room_type = models.ForeignKey(RoomType, on_delete=models.PROTECT, related_name='reservations')
    check_in = models.DateField(db_index=True)
    check_out = models.DateField(db_index=True)
    guests_count = models.PositiveIntegerField(default=1)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CONFIRMED, db_index=True)
    
    # Financial Breakdown
    nightly_rate = models.DecimalField(max_digits=10, decimal_places=2)
    num_nights = models.PositiveIntegerField(default=1)
    room_subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    service_fee = models.DecimalField(max_digits=10, decimal_places=2)
    addons_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Sandbox Payment Details
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PAID)
    payment_method = models.CharField(max_length=50, default='SANDBOX_CARD')
    transaction_id = models.CharField(max_length=64, blank=True, default='')
    paid_at = models.DateTimeField(null=True, blank=True)

    # Lifecycle Milestones
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_out_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                check=Q(check_out__gt=F('check_in')),
                name='reservation_check_out_after_check_in'
            ),
        ]
        indexes = [
            models.Index(fields=['room', 'check_in', 'check_out', 'status']),
            models.Index(fields=['status', 'check_in']),
        ]

    def __str__(self):
        return f"{self.booking_reference} - {self.guest_name} (Room {self.room.room_number}: {self.check_in} to {self.check_out}) [{self.get_status_display()}]"

    @property
    def is_active_stay(self):
        return self.status in [self.Status.CONFIRMED, self.Status.CHECKED_IN]

    @property
    def can_cancel(self):
        return self.status == self.Status.CONFIRMED

    @property
    def can_check_in(self):
        return self.status == self.Status.CONFIRMED

    @property
    def can_check_out(self):
        return self.status == self.Status.CHECKED_IN


class BookingAuditLog(models.Model):
    """
    Immutable audit trail for material operational and business events.
    Records state transitions, user actor, timestamps, and context payload.
    """
    class Action(models.TextChoices):
        HOLD_CREATED = 'HOLD_CREATED', _('Temporary Hold Created')
        HOLD_EXPIRED = 'HOLD_EXPIRED', _('Hold Expired')
        BOOKING_CONFIRMED = 'BOOKING_CONFIRMED', _('Booking Confirmed & Paid')
        CHECKED_IN = 'CHECKED_IN', _('Guest Checked In')
        CHECKED_OUT = 'CHECKED_OUT', _('Guest Checked Out')
        CANCELLED = 'CANCELLED', _('Booking Cancelled')
        ROOM_STATUS_CHANGED = 'ROOM_STATUS_CHANGED', _('Room Housekeeping Status Changed')
        RATE_UPDATED = 'RATE_UPDATED', _('Room Rate Modified')
        ROOM_CREATED = 'ROOM_CREATED', _('Physical Room Added')

    reservation = models.ForeignKey(Reservation, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=30, choices=Action.choices)
    title = models.CharField(max_length=200)
    details = models.TextField(blank=True, default='')
    ip_address = models.CharField(max_length=45, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        actor = self.user.email if self.user else 'System'
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {self.get_action_display()} by {actor}"
