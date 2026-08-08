from django.db import models


class Notification(models.Model):
    """
    A lightweight activity feed shown on the admin dashboard bell.
    Every meaningful platform event — new signup, new booking, booking
    assigned/completed/cancelled, beautician approved — calls
    notify_admin(...) which creates one of these. There's no per-admin
    targeting: with a small admin team, "every admin sees every event" is
    simpler and safer than building a subscription system.
    """
    CATEGORY_CHOICES = (
        ("signup", "New signup"),
        ("booking", "Booking"),
        ("beautician", "Beautician"),
        ("system", "System"),
    )

    message = models.CharField(max_length=255)
    link = models.CharField(max_length=255, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="system")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.message
