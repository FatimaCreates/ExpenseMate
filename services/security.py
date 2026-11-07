import hashlib


def hash_password(password):
    """SHA-256 hex digest of the password. Plain text is never stored."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()
