class DuplicateRecordError(Exception):
    """A UNIQUE constraint was violated (e.g. username or category already exists)."""
