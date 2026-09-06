from django.contrib import admin
from .models import User
from django.contrib.auth.admin import UserAdmin


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Role Info", {"fields": ("role",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Role Info", {"fields": ("role",)}),)