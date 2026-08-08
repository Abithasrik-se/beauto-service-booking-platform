from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from accounts.decorators import role_required
from accounts.forms import BeauticianProfileForm
from notifications.emails import (
    send_booking_received_email,
    send_booking_assigned_email,
    send_booking_status_email,
)
from notifications.services import notify_admin
from services.models import ServicePackage
from .forms import BookingForm, RescheduleForm
from .models import Booking
from .utils import find_nearest_available_beautician


# ---------------------------------------------------------------- Customer
@role_required("customer")
def book_package(request, package_id):
    package = get_object_or_404(ServicePackage, pk=package_id, is_active=True)

    if request.method == "POST":
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.customer = request.user
            booking.package = package
            booking.package_price = package.price
            booking.platform_fee = package.service.platform_fee
            booking.save()

            send_booking_received_email(booking)
            notify_admin(
                f"New booking: {package.service.name} by {request.user.username}",
                link="/panel/bookings/queue/", category="booking",
            )

            # Try to auto-match immediately; if nobody qualifies yet it
            # stays 'pending' and shows up in the admin's assignment queue.
            beautician, distance_km = find_nearest_available_beautician(booking)
            if beautician:
                booking.beautician = beautician
                booking.status = Booking.STATUS_ASSIGNED
                booking.save()
                send_booking_assigned_email(booking)
                notify_admin(
                    f"Auto-assigned {beautician.username} to booking #{booking.pk}",
                    link="/panel/bookings/all/", category="booking",
                )
                messages.success(request, f"Booked! Matched with a beautician ~{distance_km:.1f} km away.")
            else:
                messages.info(request, "Booking received! We're finding a nearby beautician for your slot.")

            return redirect("bookings:customer_dashboard")
    else:
        form = BookingForm()

    return render(request, "customer/book_package.html", {"form": form, "package": package})


@role_required("customer")
def customer_dashboard(request):
    bookings = Booking.objects.filter(customer=request.user).select_related(
        "package__service", "beautician"
    )
    return render(request, "customer/dashboard.html", {"bookings": bookings})


@role_required("customer")
def reschedule_booking(request, pk):
    booking = get_object_or_404(Booking, pk=pk, customer=request.user)
    if not booking.can_be_modified_by_customer():
        messages.error(request, "This booking can no longer be rescheduled.")
        return redirect("bookings:customer_dashboard")

    if request.method == "POST":
        form = RescheduleForm(request.POST, instance=booking)
        if form.is_valid():
            form.save()
            booking.reschedule_count += 1
            booking.save()
            if booking.beautician:
                send_booking_status_email(booking)
            notify_admin(f"Booking #{booking.pk} rescheduled by customer", category="booking")
            messages.success(request, "Booking rescheduled.")
            return redirect("bookings:customer_dashboard")
    else:
        form = RescheduleForm(instance=booking)

    return render(request, "customer/reschedule_booking.html", {"form": form, "booking": booking})


@role_required("customer")
def cancel_booking(request, pk):
    booking = get_object_or_404(Booking, pk=pk, customer=request.user)
    if booking.can_be_modified_by_customer():
        booking.status = Booking.STATUS_CANCELLED
        booking.save()
        if booking.beautician:
            send_booking_status_email(booking)
        notify_admin(f"Booking #{booking.pk} cancelled by customer", category="booking")
        messages.success(request, "Booking cancelled.")
    return redirect("bookings:customer_dashboard")


# --------------------------------------------------------------- Beautician
@role_required("beautician")
def beautician_dashboard(request):
    profile = getattr(request.user, "beautician_profile", None)
    all_orders = Booking.objects.filter(beautician=request.user).select_related("package__service", "customer")

    pending_orders = all_orders.filter(status=Booking.STATUS_ASSIGNED, slot_start__gte=timezone.now())
    completed_orders = all_orders.filter(status=Booking.STATUS_COMPLETED)
    total_customers = all_orders.values("customer").distinct().count()

    context = {
        "profile": profile,
        "pending_orders": pending_orders,
        "completed_orders": completed_orders,
        "all_orders": all_orders,
        "stats": {
            "total_customers": total_customers,
            "completed_count": completed_orders.count(),
            "pending_count": pending_orders.count(),
        },
    }
    return render(request, "beautician/dashboard.html", context)


@role_required("beautician")
def mark_completed(request, pk):
    booking = get_object_or_404(Booking, pk=pk, beautician=request.user, status=Booking.STATUS_ASSIGNED)
    booking.status = Booking.STATUS_COMPLETED
    booking.save()
    send_booking_status_email(booking)
    notify_admin(f"Booking #{booking.pk} marked completed by {request.user.username}", category="booking")
    messages.success(request, "Marked as completed.")
    return redirect("bookings:beautician_dashboard")


@role_required("beautician")
def update_profile(request):
    profile = request.user.beautician_profile
    if request.method == "POST":
        form = BeauticianProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("bookings:beautician_dashboard")
    else:
        form = BeauticianProfileForm(instance=profile)
    return render(request, "beautician/update_profile.html", {"form": form})
