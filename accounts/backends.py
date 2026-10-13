"""Authenticate against legacy Flask password hashes and upgrade them on first login.

The dump contains unsalted hex digests: MD5 (32 chars) and SHA-256 (64 chars).
On a successful login the password is re-hashed with Django's PBKDF2.
"""
import hashlib
from hmac import compare_digest

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


def _legacy_match(raw: str, stored: str) -> bool:
    if len(stored) == 32:
        digest = hashlib.md5(raw.encode("utf-8")).hexdigest()
    elif len(stored) == 64:
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    else:
        return False
    return compare_digest(digest, stored)


class LegacyPasswordBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        try:
            user = User.objects.select_related("role").get(username=username)
        except User.DoesNotExist:
            User().set_password(password)  # timing equalisation
            return None
        if "$" not in user.password:  # not a Django-format hash -> legacy
            if password and _legacy_match(password, user.password):
                user.set_password(password)
                user.save(update_fields=["password"])
                return user
            return None
        return user if user.check_password(password) else None

    def get_user(self, user_id):
        User = get_user_model()
        return User.objects.select_related("role").filter(pk=user_id).first()
