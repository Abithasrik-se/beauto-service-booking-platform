from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.signup_landing, name="signup_landing"),
    path("signup/customer/", views.register_customer, name="register_customer"),
    path("signup/beautician/", views.register_beautician, name="register_beautician"),
    path("verification-sent/", views.verification_sent, name="verification_sent"),
    path("verify/<uidb64>/<token>/", views.VerifyEmailView.as_view(), name="verify_email"),

    path("login/customer/", views.login_customer, name="login_customer"),
    path("login/beautician/", views.login_beautician, name="login_beautician"),
    path("login/admin/", views.login_admin, name="login_admin"),
    path("login/admin/totp-setup/", views.totp_setup, name="totp_setup"),
    path("login/admin/totp-verify/", views.totp_verify, name="totp_verify"),

    path("logout/", views.smart_logout, name="logout"),
]
