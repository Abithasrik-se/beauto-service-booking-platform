from django.conf import settings
from django.db import models


class Booking(models.Model):
    STATUS_PENDING = "pending"       # created, no beautician yet
    STATUS_ASSIGNED = "assigned"     # beautician appointed (by admin or auto-match)
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending assignment"),
        (STATUS_ASSIGNED, "Assigned"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
    )

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookings",
        limit_choices_to={"role": "customer"},
    )
    package = models.ForeignKey("services.ServicePackage", on_delete=models.CASCADE, related_name="bookings")
    beautician = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assigned_bookings", limit_choices_to={"role": "beautician"},
    )

    address = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()

    slot_start = models.DateTimeField()
    slot_end = models.DateTimeField()

    # Snapshotted at booking time so historical revenue reporting doesn't
    # shift if an admin edits package prices later.
    package_price = models.DecimalField(max_digits=8, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=8, decimal_places=2)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    notes = models.TextField(blank=True)
    reschedule_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-slot_start"]

    def __str__(self):
        return f"{self.package} for {self.customer} @ {self.slot_start:%d %b %Y %H:%M}"

    def total_amount(self):
        return self.package_price + self.platform_fee

    def can_be_modified_by_customer(self):
        return self.status in (self.STATUS_PENDING, self.STATUS_ASSIGNED)

    def maps_url(self):
        return f"https://www.google.com/maps/search/?api=1&query={self.latitude},{self.longitude}"
