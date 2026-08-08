"""
Role-based access control, implemented as view decorators.

Django's built-in @login_required always redirects to one LOGIN_URL. This
project has three separate login pages (one per role), so plain
@login_required can't do the right thing — it wouldn't know whether to
send an unauthenticated visitor to the customer, beautician, or admin
login page.

@role_required(...) fixes that: it checks the role AND picks the correct
login page to bounce to. This is the mechanism that actually enforces
"only beauticians can see /bookings/beautician/..." etc. Every dashboard
view in bookings/ and adminpanel/ is wrapped in one of these.
"""

from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def role_required(*roles):
    """Usage: @role_required("customer")  or  @role_required("admin")"""

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            user = request.user

            if not user.is_authenticated:
                # Send them to whichever login page matches what they were
                # trying to reach, so the redirect-after-login lands right.
                login_url_name = {
                    "customer": "accounts:login_customer",
                    "beautician": "accounts:login_beautician",
                    "admin": "accounts:login_admin",
                }.get(roles[0], "accounts:login_customer")
                messages.info(request, "Please log in to continue.")
                return redirect(login_url_name)

            allowed = any(
                (r == "admin" and user.is_admin_role())
                or (r != "admin" and user.role == r)
                for r in roles
            )
            if not allowed:
                messages.error(request, "You don't have access to that page.")
                return redirect("pages:home")

            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator
