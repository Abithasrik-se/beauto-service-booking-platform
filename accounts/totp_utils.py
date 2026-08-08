"""Generates the QR code an admin scans into Google Authenticator (or any
TOTP app — Authy, Microsoft Authenticator, etc. all speak the same
standard, RFC 6238). We return a data: URI so the image can be embedded
directly in the template with no extra media file or view needed."""

import base64
from io import BytesIO

import pyotp
import qrcode

from django.conf import settings


def generate_qr_code_data_uri(user):
    totp = pyotp.TOTP(user.totp_secret)
    provisioning_uri = totp.provisioning_uri(name=user.email, issuer_name=settings.TOTP_ISSUER_NAME)

    img = qrcode.make(provisioning_uri)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
