from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'id',
        'email',
        'username',
        'first_name',
        'last_name',
        'is_staff'
    )
    search_fields = (
        'email',
        'username',
        'first_name',
        'last_name'
    )
    list_filter = (
        'is_staff',
        'is_superuser',
        'is_active',
        'groups'
    )
    ordering = ('id',)