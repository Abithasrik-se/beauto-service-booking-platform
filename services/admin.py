from django.contrib import admin

from .models import ServiceCategory, Service, ServicePackage


class ServicePackageInline(admin.TabularInline):
    model = ServicePackage
    extra = 1


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "icon", "order")


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "platform_fee", "is_active")
    list_filter = ("category", "is_active")
    inlines = [ServicePackageInline]


@admin.register(ServicePackage)
class ServicePackageAdmin(admin.ModelAdmin):
    list_display = ("service", "name", "price", "duration_minutes", "is_active")
