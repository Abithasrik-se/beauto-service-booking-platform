from django.core.management.base import BaseCommand

from services.models import ServiceCategory, Service, ServicePackage

DATA = {
    "Makeup": {
        "icon": "💄",
        "services": [
            ("Bridal Makeup", 99, [
                ("Classic Bridal", 4999, 120, "HD makeup, draping, and trial session."),
                ("Bridal Deluxe", 8999, 150, "Airbrush makeup with premium products and hairstyling."),
            ]),
            ("Party Makeup", 49, [
                ("Everyday Glam", 1499, 45, "Light everyday makeup for outings."),
                ("Party Glam", 2499, 60, "Full glam makeup for events and parties."),
            ]),
        ],
    },
    "Mehndi": {
        "icon": "🌿",
        "services": [
            ("Bridal Mehndi", 99, [
                ("Front Hand Only", 2499, 90, "Intricate bridal design, front hand."),
                ("Full Hand & Leg", 4499, 180, "Full bridal mehndi, front & back, hands and legs."),
            ]),
            ("Party Mehndi", 29, [
                ("Simple Design", 599, 30, "Simple mehndi design for guests."),
                ("Medium Design", 999, 45, "Detailed mehndi pattern for special events."),
            ]),
        ],
    },
    "Hair": {
        "icon": "💇",
        "services": [
            ("Hair Styling", 39, [
                ("Blow Dry & Curls", 699, 45, "Blow-dry with curls or straightening."),
                ("Bridal Updo", 1999, 75, "Elegant bridal hairstyling with accessories."),
            ]),
            ("Hair Spa", 39, [
                ("Basic Hair Spa", 899, 60, "Nourishing treatment for dry or damaged hair."),
                ("Keratin Hair Spa", 1799, 90, "Deep conditioning keratin treatment."),
            ]),
        ],
    },
    "Skincare": {
        "icon": "✨",
        "services": [
            ("Facial", 39, [
                ("Classic Facial", 899, 60, "Deep cleanse, exfoliation, and hydration."),
                ("Gold Facial", 1599, 75, "Brightening gold facial with massage."),
            ]),
            ("Threading & Waxing", 19, [
                ("Face Threading", 199, 20, "Eyebrows, upper lip, and chin threading."),
                ("Full Arms & Legs Waxing", 799, 45, "Complete waxing for arms and legs."),
            ]),
        ],
    },
    "Nails": {
        "icon": "💅",
        "services": [
            ("Manicure & Pedicure", 29, [
                ("Classic Mani-Pedi", 799, 60, "Nail care and polish for hands and feet."),
                ("Spa Mani-Pedi", 1299, 80, "Spa treatment with scrub, mask, and massage."),
            ]),
        ],
    },
}


class Command(BaseCommand):
    help = "Seed demo categories, services, and packages matching Beauto's real focus areas."

    def handle(self, *args, **options):
        created_services, created_packages = 0, 0
        for order, (cat_name, cat_data) in enumerate(DATA.items()):
            category, _ = ServiceCategory.objects.get_or_create(
                name=cat_name, defaults={"icon": cat_data["icon"], "order": order}
            )
            for service_name, platform_fee, packages in cat_data["services"]:
                service, was_created = Service.objects.get_or_create(
                    name=service_name, category=category,
                    defaults={"platform_fee": platform_fee, "description": f"Professional {service_name.lower()} at your doorstep."},
                )
                created_services += int(was_created)
                for pkg_name, price, duration, desc in packages:
                    _, pkg_created = ServicePackage.objects.get_or_create(
                        service=service, name=pkg_name,
                        defaults={"price": price, "duration_minutes": duration, "description": desc},
                    )
                    created_packages += int(pkg_created)

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {created_services} services and {created_packages} packages across {len(DATA)} categories."
        ))
