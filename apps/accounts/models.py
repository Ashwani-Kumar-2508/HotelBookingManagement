from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', _('Hotel Administrator')
        STAFF = 'STAFF', _('Front Desk & Housekeeping Staff')
        GUEST = 'GUEST', _('Hotel Guest')

    email = models.EmailField(_('email address'), unique=True)
    phone_number = models.CharField(max_length=20, blank=True, default='')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.GUEST)
    department = models.CharField(max_length=50, blank=True, default='', help_text=_('For staff: Front Desk, Housekeeping, etc.'))
    vip_status = models.BooleanField(default=False)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['date_joined']

    def __str__(self):
        full_name = self.get_full_name().strip()
        display = full_name if full_name else self.email
        return f"{display} [{self.get_role_display()}]"

    @property
    def is_hotel_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_hotel_staff(self):
        return self.role in [self.Role.STAFF, self.Role.ADMIN] or self.is_superuser

    @property
    def is_guest(self):
        return self.role == self.Role.GUEST
