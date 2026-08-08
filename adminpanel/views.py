from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from accounts.decorators import role_required
from accounts.models import BeauticianProfile, User
from bookings.models import Booking
from bookings.utils import find_nearest_available_beautician, nearby_available_beauticians
from notifications.emails import (
    send_beautician_approved_email,
    send_beautician_rejected_email,
    send_booking_assigned_email,
)
from notifications.models import Notification
from services.models import Service, ServicePackage, ServiceCategory
from .forms import ServiceForm, ServicePackageForm, ServiceCategoryForm


# ------------------------------------------------------------------ Overview
@role_required("admin")
def dashboard(request):
    completed = Booking.objects.filter(status=Booking.STATUS_COMPLETED)
    platform_revenue = completed.aggregate(total=Sum("platform_fee"))["total"] or 0
    # Sum(a)+Sum(b) can behave oddly across DB backends on empty querysets,
    # so compute gross revenue defensively in Python instead.
    gross_revenue = sum((b.total_amount() for b in completed), start=0)

    context = {
        "total_customers": User.objects.filter(role=User.ROLE_CUSTOMER).count(),
        "total_beauticians": User.objects.filter(role=User.ROLE_BEAUTICIAN).count(),
        "pending_approvals": BeauticianProfile.objects.filter(is_approved=False, rejected=False).count(),
        "pending_bookings": Booking.objects.filter(status=Booking.STATUS_PENDING).count(),
        "active_bookings": Booking.objects.filter(status=Booking.STATUS_ASSIGNED).count(),
        "completed_bookings": completed.count(),
        "cancelled_bookings": Booking.objects.filter(status=Booking.STATUS_CANCELLED).count(),
        "gross_revenue": gross_revenue,
        "platform_revenue": platform_revenue,
        "recent_notifications": Notification.objects.all()[:8],
    }
    return render(request, "admin/dashboard.html", context)


@role_required("admin")
def notifications_list(request):
    notifications = Notification.objects.all()
    if request.method == "POST":
        Notification.objects.filter(is_read=False).update(is_read=True)
        messages.success(request, "All notifications marked as read.")
        return redirect("adminpanel:notifications")
    return render(request, "admin/notifications.html", {"notifications": notifications})


# ------------------------------------------------------------- Beauticians
@role_required("admin")
def beautician_approvals(request):
    profiles = BeauticianProfile.objects.filter(rejected=False).select_related("user").order_by("is_approved")
    return render(request, "admin/beautician_approvals.html", {"profiles": profiles})


@role_required("admin")
def approve_beautician(request, pk):
    profile = get_object_or_404(BeauticianProfile, pk=pk)
    profile.is_approved = True
    profile.approved_at = timezone.now()
    profile.save()
    send_beautician_approved_email(profile.user)
    messages.success(request, f"{profile.user.get_full_name() or profile.user.username} approved.")
    return redirect("adminpanel:beautician_approvals")


@role_required("admin")
def reject_beautician(request, pk):
    profile = get_object_or_404(BeauticianProfile, pk=pk)
    profile.is_approved = False
    profile.rejected = True
    profile.save()
    send_beautician_rejected_email(profile.user)
    messages.info(request, f"{profile.user.get_full_name() or profile.user.username} rejected.")
    return redirect("adminpanel:beautician_approvals")


# ------------------------------------------------------------------ Services
@role_required("admin")
def service_list(request):
    services = Service.objects.select_related("category").prefetch_related("packages")
    categories = ServiceCategory.objects.all()
    return render(request, "admin/service_list.html", {"services": services, "categories": categories})


@role_required("admin")
def category_create(request):
    if request.method == "POST":
        form = ServiceCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Category created.")
            return redirect("adminpanel:service_list")
    else:
        form = ServiceCategoryForm()
    return render(request, "admin/category_form.html", {"form": form})


@role_required("admin")
def service_create(request):
    if request.method == "POST":
        form = ServiceForm(request.POST)
        if form.is_valid():
            service = form.save()
            messages.success(request, "Service created — now add at least one package.")
            return redirect("adminpanel:package_create", service_id=service.pk)
    else:
        form = ServiceForm()
    return render(request, "admin/service_form.html", {"form": form})


@role_required("admin")
def service_edit(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == "POST":
        form = ServiceForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, "Service updated.")
            return redirect("adminpanel:service_list")
    else:
        form = ServiceForm(instance=service)
    return render(request, "admin/service_form.html", {"form": form, "service": service})


@role_required("admin")
def package_create(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    if request.method == "POST":
        form = ServicePackageForm(request.POST)
        if form.is_valid():
            package = form.save(commit=False)
            package.service = service
            package.save()
            messages.success(request, f"Package '{package.name}' added to {service.name}.")
            return redirect("adminpanel:service_list")
    else:
        form = ServicePackageForm()
    return render(request, "admin/package_form.html", {"form": form, "service": service})


# ----------------------------------------------------------------- Bookings
@role_required("admin")
def booking_queue(request):
    bookings = Booking.objects.filter(status=Booking.STATUS_PENDING).select_related("package__service", "customer")
    return render(request, "admin/booking_queue.html", {"bookings": bookings})


@role_required("admin")
def all_bookings(request):
    bookings = Booking.objects.all().select_related("package__service", "customer", "beautician")
    return render(request, "admin/all_bookings.html", {"bookings": bookings})


@role_required("admin")
def auto_assign(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    beautician, distance_km = find_nearest_available_beautician(booking)
    if beautician:
        booking.beautician = beautician
        booking.status = Booking.STATUS_ASSIGNED
        booking.save()
        send_booking_assigned_email(booking)
        messages.success(request, f"Auto-assigned {beautician.username} (~{distance_km:.1f} km away).")
    else:
        messages.warning(request, "No approved, in-range, available beautician found for this slot.")
    return redirect("adminpanel:booking_queue")


@role_required("admin")
def assign_booking(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    candidates = nearby_available_beauticians(booking)

    if request.method == "POST":
        beautician_id = request.POST.get("beautician_id")
        beautician = get_object_or_404(User, pk=beautician_id, role=User.ROLE_BEAUTICIAN)
        booking.beautician = beautician
        booking.status = Booking.STATUS_ASSIGNED
        booking.save()
        send_booking_assigned_email(booking)
        messages.success(request, f"Assigned to {beautician.username}.")
        return redirect("adminpanel:booking_queue")

    return render(request, "admin/assign_booking.html", {"booking": booking, "candidates": candidates})
