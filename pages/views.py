from django.shortcuts import render

from services.models import ServiceCategory, Service


def home(request):
    categories = ServiceCategory.objects.prefetch_related("services__packages")[:5]
    featured_services = Service.objects.filter(is_active=True).select_related("category")[:6]
    return render(request, "pages/home.html", {"categories": categories, "featured_services": featured_services})


def about(request):
    return render(request, "pages/about.html")


def contact(request):
    return render(request, "pages/contact.html")


def service_catalog(request):
    """The tabbed/filterable services page. `category` query param drives
    the active tab; everything is rendered server-side (no JS framework
    needed) — the tabs are just links/buttons with ?category=<id>."""
    categories = ServiceCategory.objects.prefetch_related("services__packages")
    active_category_id = request.GET.get("category")

    services = Service.objects.filter(is_active=True).select_related("category").prefetch_related("packages")
    if active_category_id:
        services = services.filter(category_id=active_category_id)

    return render(request, "pages/services.html", {
        "categories": categories,
        "services": services,
        "active_category_id": int(active_category_id) if active_category_id else None,
    })
