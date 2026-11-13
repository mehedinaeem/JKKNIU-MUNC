"""Private links are encrypted only while waiting in the existing email queue.

Invitation records contain SHA-256 hashes only. Django's high-entropy server key
is domain-separated using HKDF; neither key nor ciphertext belongs in React.
"""
import base64
from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

SECURITY_TYPES = {'membership_invitation', 'membership_password_reset', 'membership_email_verification'}
PREFIX = 'munc-encrypted:v1:'


def cipher():
    keys = [settings.SECRET_KEY, *settings.SECRET_KEY_FALLBACKS]
    return MultiFernet([Fernet(base64.urlsafe_b64encode(HKDF(algorithm=hashes.SHA256(), length=32,
        salt=b'munc-membership-mail-v1', info=b'private-queued-email').derive(key.encode()))) for key in keys])


def seal(value):
    return PREFIX + cipher().encrypt(value.encode()).decode()


def unseal(value):
    if not value.startswith(PREFIX): raise InvalidToken()
    return cipher().decrypt(value[len(PREFIX):].encode()).decode()
