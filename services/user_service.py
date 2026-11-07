"""Registration, login and currency rules (Services layer)."""

from constants import DEFAULT_CATEGORIES, SUPPORTED_CURRENCIES
from repositories.category_repository import CategoryRepository
from repositories.errors import DuplicateRecordError
from repositories.user_repository import UserRepository
from services.security import hash_password


class UserService:

    def __init__(self, user_repo=None, category_repo=None):
        self._users = user_repo or UserRepository()
        self._categories = category_repo or CategoryRepository()

    def register(self, username, password, currency="PKR"):
        """Create the account and seed default categories. Returns the new user id;
        raises ValueError(message) for empty fields or a taken username."""
        username = (username or "").strip()
        if not username:
            raise ValueError("Username cannot be empty.")
        if not password:
            raise ValueError("Password cannot be empty.")
        if currency not in SUPPORTED_CURRENCIES:
            currency = "PKR"
        try:
            user_id = self._users.create(username, hash_password(password), currency)
        except DuplicateRecordError:
            raise ValueError("Username already exists.")
        self._categories.add_many_ignoring_duplicates(user_id, DEFAULT_CATEGORIES)
        return user_id

    def verify(self, username, password):
        """The user's dict if the credentials are right, else None."""
        user = self._users.find_by_username(username)
        if user and user["password_hash"] == hash_password(password):
            return user
        return None

    def get_user(self, user_id):
        return self._users.find_by_id(user_id)

    def set_currency(self, user_id, currency):
        if currency not in SUPPORTED_CURRENCIES:
            raise ValueError(f"Unsupported currency '{currency}'.")
        self._users.update_currency(user_id, currency)
