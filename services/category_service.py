"""Category rules (Services layer)."""

from constants import DEFAULT_CATEGORIES
from repositories.category_repository import CategoryRepository
from repositories.errors import DuplicateRecordError


class CategoryService:

    def __init__(self, category_repo=None):
        self._categories = category_repo or CategoryRepository()

    def list_names(self, user_id):
        return self._categories.list_names(user_id)

    def add_category(self, user_id, name):
        """Returns the saved name; raises ValueError(message) if empty or a case-insensitive duplicate."""
        name = (name or "").strip()
        if not name:
            raise ValueError("Category name cannot be empty.")
        if name.lower() in {c.lower() for c in self._categories.list_names(user_id)}:
            raise ValueError(f"Category '{name}' already exists.")
        try:
            self._categories.add(user_id, name)
        except DuplicateRecordError:
            raise ValueError(f"Category '{name}' already exists.")
        return name

    def delete_category(self, user_id, name):
        """A category that transactions or budgets still use cannot be deleted."""
        category_id = self._categories.find_id(user_id, name)
        if category_id is not None and self._categories.usage_count(category_id) > 0:
            raise ValueError(f"Category '{name}' is used by existing transactions or budgets.")
        self._categories.delete(user_id, name)

    def ensure_defaults(self, user_id):
        """Make sure the user has at least the default categories (case-insensitive)."""
        existing = {c.lower() for c in self._categories.list_names(user_id)}
        missing = [n for n in DEFAULT_CATEGORIES if n.lower() not in existing]
        if missing:
            self._categories.add_many_ignoring_duplicates(user_id, missing)
