from django.urls import path

from . import views

app_name = "pages"

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("services/", views.service_catalog, name="services"),
    path("contact/", views.contact, name="contact"),
]
