from django.urls import path

from . import views

app_name = "bookings"

urlpatterns = [
    path("package/<int:package_id>/book/", views.book_package, name="book_package"),

    path("customer/", views.customer_dashboard, name="customer_dashboard"),
    path("customer/<int:pk>/reschedule/", views.reschedule_booking, name="reschedule_booking"),
    path("customer/<int:pk>/cancel/", views.cancel_booking, name="cancel_booking"),

    path("beautician/", views.beautician_dashboard, name="beautician_dashboard"),
    path("beautician/profile/", views.update_profile, name="update_profile"),
    path("beautician/<int:pk>/complete/", views.mark_completed, name="mark_completed"),
]
