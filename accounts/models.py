from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    One table, three roles. Rather than three separate Django auth models,
    every account — customer, beautician, admin — is a row here with a
    `role` flag. This is the standard RBAC pattern for small-to-mid apps:
    cheap to query ("all customers" is just User.objects.filter(role=...)),
    and every foreign key elsewhere (Booking.customer, Booking.beautician)
    can point at the same table.

    Two independent gates control whether someone can log in:
      1. `is_active`   — flips True only after email verification.
      2. BeauticianProfile.is_approved — a SECOND gate that only applies
         to beauticians: verified but not yet approved by admin.
    Admins get a THIRD gate: TOTP (Google Authenticator) on top of
    password, checked in accounts.views.
    """

    ROLE_CUSTOMER = "customer"
    ROLE_BEAUTICIAN = "beautician"
    ROLE_ADMIN = "admin"
    ROLE_CHOICES = (
        (ROLE_CUSTOMER, "Customer"),
        (ROLE_BEAUTICIAN, "Beautician"),
        (ROLE_ADMIN, "Admin"),
    )

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CUSTOMER)
    phone = models.CharField(max_length=15, blank=True)
    email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # New customer/beautician accounts start inactive until email
    # verification (accounts.views.VerifyEmailView flips this on).
    is_active = models.BooleanField(default=False)

    # --- Admin two-factor auth (TOTP / Google Authenticator) ---------
    totp_secret = models.CharField(max_length=64, blank=True)
    totp_enabled = models.BooleanField(default=False)

    def is_customer(self):
        return self.role == self.ROLE_CUSTOMER

    def is_beautician(self):
        return self.role == self.ROLE_BEAUTICIAN

    def is_admin_role(self):
        return self.role == self.ROLE_ADMIN or self.is_superuser

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"


class ServiceSkill(models.Model):
    """Reused from services.ServiceCategory conceptually, but kept
    independent so a beautician's declared skills don't hard-depend on
    the services app importing accounts (avoids circular imports)."""
    name = models.CharField(max_length=60, unique=True)

    def __str__(self):
        return self.name


class BeauticianProfile(models.Model):
    """Extra data + admin-approval state for beautician accounts.
    Every beautician User has exactly one of these (OneToOne)."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="beautician_profile")
    bio = models.TextField(blank=True)
    skills = models.ManyToManyField(ServiceSkill, blank=True, related_name="beauticians")
    profile_photo = models.ImageField(upload_to="beautician_photos/", blank=True, null=True)

    address = models.CharField(max_length=255, blank=True)
    latitude = models.FloatField(help_text="Base location latitude, used for nearby matching")
    longitude = models.FloatField(help_text="Base location longitude, used for nearby matching")
    service_radius_km = models.FloatField(default=15)

    available_from = models.TimeField(default="09:00", help_text="Daily availability start time")
    available_to = models.TimeField(default="19:00", help_text="Daily availability end time")

    is_approved = models.BooleanField(default=False)
    rejected = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} — Beautician"

    def status_label(self):
        if self.rejected:
            return "Rejected"
        if self.is_approved:
            return "Approved"
        return "Pending approval"
