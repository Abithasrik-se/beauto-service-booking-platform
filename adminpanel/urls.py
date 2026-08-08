from django.urls import path

from . import views

app_name = "adminpanel"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("notifications/", views.notifications_list, name="notifications"),

    path("beauticians/", views.beautician_approvals, name="beautician_approvals"),
    path("beauticians/<int:pk>/approve/", views.approve_beautician, name="approve_beautician"),
    path("beauticians/<int:pk>/reject/", views.reject_beautician, name="reject_beautician"),

    path("services/", views.service_list, name="service_list"),
    path("services/category/new/", views.category_create, name="category_create"),
    path("services/new/", views.service_create, name="service_create"),
    path("services/<int:pk>/edit/", views.service_edit, name="service_edit"),
    path("services/<int:service_id>/packages/new/", views.package_create, name="package_create"),

    path("bookings/queue/", views.booking_queue, name="booking_queue"),
    path("bookings/all/", views.all_bookings, name="all_bookings"),
    path("bookings/<int:pk>/auto-assign/", views.auto_assign, name="auto_assign"),
    path("bookings/<int:pk>/assign/", views.assign_booking, name="assign_booking"),
]
