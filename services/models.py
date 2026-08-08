from django.db import models


class ServiceCategory(models.Model):
    """Powers the tabs/filters on the public Services page
    (Makeup / Mehndi / Hair / Skincare / Nails ...)."""
    name = models.CharField(max_length=60, unique=True)
    icon = models.CharField(max_length=10, blank=True, help_text="An emoji works fine, e.g. 💇")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "Service categories"

    def __str__(self):
        return self.name


class Service(models.Model):
    """A bookable service, e.g. 'Bridal Makeup'. Doesn't have a price
    itself — price lives on ServicePackage, since a service is offered
    at multiple price/duration tiers (Basic / Premium / Bridal Deluxe)."""

    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name="services")
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    platform_fee = models.DecimalField(
        max_digits=8, decimal_places=2, default=49,
        help_text="Fixed platform fee added on top of every package's price for this service.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def starting_price(self):
        cheapest = self.packages.order_by("price").first()
        return cheapest.price if cheapest else None


class ServicePackage(models.Model):
    """One priced tier of a Service. This is what a Booking actually
    references — booking a 'service' really means booking one of its
    packages."""

    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="packages")
    name = models.CharField(max_length=100, help_text="e.g. Basic, Premium, Bridal Deluxe")
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    duration_minutes = models.PositiveIntegerField(default=60)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["price"]

    def __str__(self):
        return f"{self.service.name} — {self.name}"

    def total_amount(self):
        return self.price + self.service.platform_fee
