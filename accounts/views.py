"""
Auth flow overview (read this once, then the code below is just detail):

  Customer/Beautician signup
    -> account created with is_active=False
    -> verification email sent
    -> user clicks link -> VerifyEmailView flips is_active=True
    -> (beautician only) ALSO needs BeauticianProfile.is_approved=True,
       set later by an admin in adminpanel
    -> can now use LoginCustomerView / LoginBeauticianView

  Admin login (two-step, like real banking/Google 2FA)
    -> Step 1 (LoginAdminView): username+password checked with
       authenticate(), but NOT logged in yet. User id stashed in
       session key 'pending_admin_id'.
    -> If this admin has never set up TOTP: redirect to totp_setup
       (shows a QR code + manual key, must be confirmed with one code
       before it's enabled).
    -> Step 2 (totp_verify): asks for the 6-digit code from Google
       Authenticator. Correct code -> django.contrib.auth.login() happens
       HERE, not in step 1. That's the whole point of 2FA: password alone
       never logs anyone in.

  Logout
    -> smart_logout captures request.user.role BEFORE calling
       django's logout() (which wipes request.user to Anonymous), so it
       can redirect back to the correct role-specific login page instead
       of one generic page.
"""

import pyotp

from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views import View

from notifications.emails import send_verification_email, send_beautician_pending_email
from notifications.services import notify_admin
from .forms import CustomerSignupForm, BeauticianSignupForm, StyledAuthenticationForm, TOTPVerifyForm
from .models import User
from .tokens import email_verification_token
from .totp_utils import generate_qr_code_data_uri


# --------------------------------------------------------------- Signup
def signup_landing(request):
    return render(request, "registration/signup_landing.html")


def register_customer(request):
    if request.method == "POST":
        form = CustomerSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            send_verification_email(user)
            notify_admin(f"New customer signed up: {user.username}", category="signup")
            return redirect("accounts:verification_sent")
    else:
        form = CustomerSignupForm()
    return render(request, "registration/register_customer.html", {"form": form})


def register_beautician(request):
    if request.method == "POST":
        form = BeauticianSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            send_verification_email(user)
            notify_admin(f"New beautician application: {user.username}", link="/panel/beauticians/", category="signup")
            return redirect("accounts:verification_sent")
    else:
        form = BeauticianSignupForm()
    return render(request, "registration/register_beautician.html", {"form": form})


def verification_sent(request):
    return render(request, "registration/verification_sent.html")


class VerifyEmailView(View):
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and email_verification_token.check_token(user, token):
            user.is_active = True
            user.email_verified = True
            user.save()

            if user.role == User.ROLE_BEAUTICIAN:
                send_beautician_pending_email(user)
                messages.success(request, "Email verified! Your profile now awaits admin approval.")
                return redirect("accounts:login_beautician")

            messages.success(request, "Email verified! You can now log in.")
            return redirect("accounts:login_customer")

        return render(request, "registration/verification_invalid.html")


# ----------------------------------------------------------- Customer login
def login_customer(request):
    return _role_login(request, User.ROLE_CUSTOMER, "registration/login_customer.html", "bookings:customer_dashboard")


def login_beautician(request):
    return _role_login(request, User.ROLE_BEAUTICIAN, "registration/login_beautician.html", "bookings:beautician_dashboard")


def _role_login(request, role, template, success_url_name):
    if request.method == "POST":
        form = StyledAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.role != role:
                messages.error(request, "That account isn't registered for this login page.")
                return render(request, template, {"form": form})

            if role == User.ROLE_BEAUTICIAN:
                profile = getattr(user, "beautician_profile", None)
                if profile and profile.rejected:
                    messages.error(request, "Your beautician application was not approved.")
                    return render(request, template, {"form": form})
                if profile and not profile.is_approved:
                    messages.warning(request, "Your profile is verified but still awaiting admin approval.")
                    return render(request, template, {"form": form})

            auth_login(request, user)
            return redirect(success_url_name)
        else:
            username = request.POST.get("username")
            existing = User.objects.filter(username=username).first()
            if existing and not existing.is_active:
                messages.warning(request, "Your email isn't verified yet — check your inbox for the link.")
    else:
        form = StyledAuthenticationForm(request)
    return render(request, template, {"form": form})


# -------------------------------------------------------------- Admin login
def login_admin(request):
    """Step 1: password only. Does NOT call auth_login() — see module docstring."""
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user is not None and user.is_admin_role():
            request.session["pending_admin_id"] = user.pk
            if not user.totp_enabled:
                return redirect("accounts:totp_setup")
            return redirect("accounts:totp_verify")

        messages.error(request, "Invalid admin credentials.")

    return render(request, "registration/login_admin.html")


def totp_setup(request):
    """Shown once per admin: generate a secret, show the QR code, and
    require ONE correct code before enabling — proves the app was actually
    scanned into their authenticator before we rely on it."""
    pending_id = request.session.get("pending_admin_id")
    if not pending_id:
        return redirect("accounts:login_admin")
    user = get_object_or_404(User, pk=pending_id)

    if not user.totp_secret:
        user.totp_secret = pyotp.random_base32()
        user.save()

    qr_data_uri = generate_qr_code_data_uri(user)

    if request.method == "POST":
        form = TOTPVerifyForm(request.POST)
        if form.is_valid():
            totp = pyotp.TOTP(user.totp_secret)
            if totp.verify(form.cleaned_data["code"], valid_window=1):
                user.totp_enabled = True
                user.save()
                auth_login(request, user)
                request.session.pop("pending_admin_id", None)
                messages.success(request, "Two-factor authentication enabled.")
                return redirect("adminpanel:dashboard")
            messages.error(request, "That code didn't match. Try the current code from your app.")
    else:
        form = TOTPVerifyForm()

    return render(request, "registration/totp_setup.html", {
        "form": form, "qr_data_uri": qr_data_uri, "secret": user.totp_secret,
    })


def totp_verify(request):
    """Step 2 for admins who already have 2FA enabled."""
    pending_id = request.session.get("pending_admin_id")
    if not pending_id:
        return redirect("accounts:login_admin")
    user = get_object_or_404(User, pk=pending_id)

    if request.method == "POST":
        form = TOTPVerifyForm(request.POST)
        if form.is_valid():
            totp = pyotp.TOTP(user.totp_secret)
            if totp.verify(form.cleaned_data["code"], valid_window=1):
                auth_login(request, user)
                request.session.pop("pending_admin_id", None)
                return redirect("adminpanel:dashboard")
            messages.error(request, "Incorrect code. Please try again.")
    else:
        form = TOTPVerifyForm()

    return render(request, "registration/totp_verify.html", {"form": form})


# -------------------------------------------------------------------- Logout
def smart_logout(request):
    """Captures the role BEFORE logging out, so we can redirect back to
    the *correct* role-specific login page instead of one generic page."""
    role = request.user.role if request.user.is_authenticated else None
    is_admin = request.user.is_admin_role() if request.user.is_authenticated else False
    auth_logout(request)

    if is_admin:
        return redirect("accounts:login_admin")
    if role == User.ROLE_BEAUTICIAN:
        return redirect("accounts:login_beautician")
    return redirect("accounts:login_customer")
