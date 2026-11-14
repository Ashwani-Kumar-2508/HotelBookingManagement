from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'get_full_name', 'role', 'vip_status', 'is_active', 'date_joined']
    list_filter = ['role', 'is_active', 'vip_status', 'is_staff']
    search_fields = ['email', 'first_name', 'last_name', 'username']
    ordering = ['-date_joined']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Hotel Profile', {
            'fields': ('role', 'phone_number', 'department', 'vip_status')
        }),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Hotel Profile', {
            'fields': ('email', 'first_name', 'last_name', 'role', 'phone_number', 'department', 'vip_status')
        }),
    )
