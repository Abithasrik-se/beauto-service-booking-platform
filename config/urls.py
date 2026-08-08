from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from accounts import views as account_views

urlpatterns = [
    path("django-admin/", admin.site.urls),  # Django's built-in admin, superuser fallback only

    path("", include("pages.urls")),          # home / about / services / contact
    path("accounts/", include("accounts.urls")),
    path("bookings/", include("bookings.urls")),
    path("panel/", include("adminpanel.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
