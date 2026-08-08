from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, BeauticianProfile, ServiceSkill


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "is_active", "email_verified", "totp_enabled", "is_staff")
    list_filter = ("role", "is_active", "email_verified")
    fieldsets = UserAdmin.fieldsets + (
        ("Role info", {"fields": ("role", "phone", "email_verified")}),
        ("Two-factor (admin only)", {"fields": ("totp_secret", "totp_enabled")}),
    )


@admin.register(BeauticianProfile)
class BeauticianProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "is_approved", "rejected", "service_radius_km", "address")
    list_filter = ("is_approved", "rejected")


@admin.register(ServiceSkill)
class ServiceSkillAdmin(admin.ModelAdmin):
    list_display = ("name",)
