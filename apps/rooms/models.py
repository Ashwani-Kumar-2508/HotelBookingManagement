from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from decimal import Decimal


class Amenity(models.Model):
    class Category(models.TextChoices):
        COMFORT = 'COMFORT', _('Comfort & Living')
        BATHROOM = 'BATHROOM', _('Bath & Wellness')
        TECH = 'TECH', _('Technology & Media')
        DINING = 'DINING', _('Food & Beverage')
        VIEW = 'VIEW', _('Views & Outdoors')

    name = models.CharField(max_length=80, unique=True)
    icon = models.CharField(max_length=40, default='check', help_text=_('Feather or Lucide icon name'))
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.COMFORT)
    description = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name_plural = _('Amenities')
        ordering = ['category', 'name']

    def __str__(self):
        return self.name


class RoomType(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    tagline = models.CharField(max_length=255, blank=True, help_text=_('Catchy 1-line summary'))
    description = models.TextField()
    base_price = models.DecimalField(max_digits=10, decimal_places=2, help_text=_('Standard weekday nightly rate'))
    weekend_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text=_('Optional weekend nightly rate'))
    max_guests = models.PositiveIntegerField(default=2, help_text=_('Maximum guest capacity'))
    bed_type = models.CharField(max_length=80, default='1 King Bed')
    size_sqft = models.PositiveIntegerField(default=450, help_text=_('Room area in square feet'))
    amenities = models.ManyToManyField(Amenity, blank=True, related_name='room_types')
    image_url = models.CharField(max_length=500, blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['base_price']

    def __str__(self):
        return f"{self.name} (${self.base_price}/night, max {self.max_guests} guests)"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.weekend_price:
            # Default weekend price is 15% higher than base weekday
            self.weekend_price = (self.base_price * Decimal('1.15')).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)

    @property
    def total_rooms_count(self):
        return self.rooms.filter(is_active=True).count()


class Room(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = 'AVAILABLE', _('Available / Inspected Clean')
        OCCUPIED = 'OCCUPIED', _('Occupied')
        DIRTY = 'DIRTY', _('Needs Cleaning / Housekeeping')
        MAINTENANCE = 'MAINTENANCE', _('Out of Order / Maintenance')

    room_number = models.CharField(max_length=20, unique=True)
    room_type = models.ForeignKey(RoomType, on_delete=models.PROTECT, related_name='rooms')
    floor = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    housekeeping_notes = models.CharField(max_length=255, blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['floor', 'room_number']

    def __str__(self):
        return f"Room {self.room_number} - {self.room_type.name} (Fl. {self.floor}) [{self.get_status_display()}]"

    @property
    def is_operational(self):
        return self.is_active and self.status != self.Status.MAINTENANCE
