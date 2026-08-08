"""Single entry point for creating admin notifications — call this instead
of Notification.objects.create(...) directly, so every call site stays
consistent and easy to grep for."""

from .models import Notification


def notify_admin(message, link="", category="system"):
    return Notification.objects.create(message=message, link=link, category=category)
