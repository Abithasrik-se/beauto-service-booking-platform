from django.contrib import admin

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "package", "customer", "beautician", "status", "slot_start", "total_amount")
    list_filter = ("status",)
    search_fields = ("customer__username", "beautician__username", "address")
