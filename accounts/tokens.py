from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """Same signed-token mechanism Django uses for password resets, but the
    hash also folds in `email_verified` so each token can only be used once —
    replaying an old verification link after the flag flips no longer works."""

    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{user.email}{user.email_verified}{timestamp}"


email_verification_token = EmailVerificationTokenGenerator()
