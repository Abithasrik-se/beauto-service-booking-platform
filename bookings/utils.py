"""
Core matching logic — the "Urban Company" part of this project.

1. haversine_km        – straight-line distance between two lat/lng points
2. has_conflict         – checks a beautician's calendar for an overlapping slot
3. find_nearest_available_beautician – ranks approved, in-range, free
   beauticians by distance and returns the closest one
4. nearby_available_beauticians      – same ranking, full list, for the
   admin's manual "assign" screen
"""

import math

from accounts.models import BeauticianProfile
from django.conf import settings


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two points, in kilometres."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def has_conflict(beautician_user, slot_start, slot_end, exclude_booking_id=None):
    """True if the beautician already has an active booking overlapping
    the given [slot_start, slot_end) window."""
    from .models import Booking  # local import avoids circular import

    qs = Booking.objects.filter(
        beautician=beautician_user,
        status=Booking.STATUS_ASSIGNED,
        slot_start__lt=slot_end,
        slot_end__gt=slot_start,
    )
    if exclude_booking_id:
        qs = qs.exclude(pk=exclude_booking_id)
    return qs.exists()


def find_nearest_available_beautician(booking):
    """Returns (beautician_user, distance_km) for the closest approved
    beautician who is free for `booking`'s slot and within range, or
    (None, None) if nobody qualifies."""

    candidates = BeauticianProfile.objects.filter(is_approved=True, rejected=False).select_related("user")

    best_user, best_distance = None, None
    for profile in candidates:
        radius = profile.service_radius_km or settings.DEFAULT_SERVICE_RADIUS_KM
        distance = haversine_km(booking.latitude, booking.longitude, profile.latitude, profile.longitude)
        if distance > radius:
            continue
        if has_conflict(profile.user, booking.slot_start, booking.slot_end, exclude_booking_id=booking.pk):
            continue
        if best_distance is None or distance < best_distance:
            best_distance, best_user = distance, profile.user

    return best_user, best_distance


def nearby_available_beauticians(booking, limit=15):
    """Full ranked list (for the admin's manual-assign dropdown)."""
    candidates = BeauticianProfile.objects.filter(is_approved=True, rejected=False).select_related("user")
    results = []
    for profile in candidates:
        radius = profile.service_radius_km or settings.DEFAULT_SERVICE_RADIUS_KM
        distance = haversine_km(booking.latitude, booking.longitude, profile.latitude, profile.longitude)
        conflict = has_conflict(profile.user, booking.slot_start, booking.slot_end, exclude_booking_id=booking.pk)
        results.append({
            "user": profile.user,
            "distance_km": round(distance, 1),
            "in_range": distance <= radius,
            "available": not conflict,
        })
    results.sort(key=lambda r: r["distance_km"])
    return results[:limit]
