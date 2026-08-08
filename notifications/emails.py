"""Every outgoing email in the platform is defined and sent from here.
Views never call django.core.mail directly — they call one of these
functions — so "what emails does this app send" has exactly one file
to grep."""

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from accounts.tokens import email_verification_token


def _send(subject, template, context, to):
    message = render_to_string(template, context)
    send_mail(
        subject=f"[Beauto] {subject}",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to],
        fail_silently=False,
    )


def send_verification_email(user):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token.make_token(user)
    link = f"{settings.SITE_DOMAIN}/accounts/verify/{uidb64}/{token}/"
    _send("Verify your email", "emails/verify_email.txt", {"user": user, "link": link}, user.email)


def send_beautician_pending_email(user):
    _send("Application received", "emails/beautician_pending.txt", {"user": user}, user.email)


def send_beautician_approved_email(user):
    link = f"{settings.SITE_DOMAIN}/accounts/login/beautician/"
    _send("You're approved!", "emails/beautician_approved.txt", {"user": user, "login_link": link}, user.email)


def send_beautician_rejected_email(user):
    _send("Application update", "emails/beautician_rejected.txt", {"user": user}, user.email)


def send_booking_received_email(booking):
    _send(
        f"Booking received — {booking.package.service.name}",
        "emails/booking_received.txt", {"booking": booking}, booking.customer.email,
    )


def send_booking_assigned_email(booking):
    _send(
        "Your beautician is confirmed",
        "emails/booking_assigned_customer.txt", {"booking": booking}, booking.customer.email,
    )
    _send(
        "New order assigned to you",
        "emails/booking_assigned_beautician.txt", {"booking": booking}, booking.beautician.email,
    )


def send_booking_status_email(booking):
    _send(
        f"Booking update: {booking.get_status_display()}",
        "emails/booking_status_update.txt", {"booking": booking}, booking.customer.email,
    )
