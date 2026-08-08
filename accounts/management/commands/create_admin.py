"""
Convenience command so setting up the first admin doesn't require a manual
Django shell session. Plain `createsuperuser` doesn't know about our custom
`role` field, so this wraps it with the right defaults.

Usage:
    python manage.py create_admin
"""

import getpass

from django.core.management.base import BaseCommand
from django.db import IntegrityError

from accounts.models import User


class Command(BaseCommand):
    help = "Create an admin account (role='admin', active, ready to set up 2FA on first login)."

    def handle(self, *args, **options):
        username = input("Admin username: ").strip()
        email = input("Admin email: ").strip()
        password = getpass.getpass("Admin password: ")
        confirm = getpass.getpass("Confirm password: ")

        if password != confirm:
            self.stderr.write(self.style.ERROR("Passwords didn't match. Aborted."))
            return

        try:
            user = User.objects.create_superuser(username=username, email=email, password=password)
        except IntegrityError:
            self.stderr.write(self.style.ERROR(f"A user named '{username}' already exists."))
            return

        user.role = User.ROLE_ADMIN
        user.is_active = True
        user.email_verified = True
        user.save()

        self.stdout.write(self.style.SUCCESS(
            f"Admin '{username}' created. Log in at /accounts/login/admin/ — "
            "you'll be walked through 2FA setup (QR code) on first login."
        ))
