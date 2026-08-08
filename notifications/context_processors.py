from .models import Notification


def unread_notifications(request):
    """Injects `unread_notification_count` into every template's context —
    used for the badge on the admin navbar bell. Cheap: one COUNT query,
    and only runs the query at all for authenticated admins."""
    if request.user.is_authenticated and getattr(request.user, "is_admin_role", lambda: False)():
        count = Notification.objects.filter(is_read=False).count()
        return {"unread_notification_count": count}
    return {}
