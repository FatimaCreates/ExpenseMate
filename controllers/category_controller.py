from controllers.result import Result
from services.category_service import CategoryService


class CategoryController:

    def __init__(self, service=None):
        self._service = service or CategoryService()

    def list_names(self, user_id):
        return Result(True, data=self._service.list_names(user_id))

    def add_category(self, user_id, name):
        if not (name or "").strip():
            return Result(False, "Please enter a category name.", error="validation")
        try:
            saved = self._service.add_category(user_id, name)
        except ValueError as exc:
            return Result(False, str(exc), error="validation")
        return Result(True, f"Category '{saved}' added! Select it above.", data=saved)

    def ensure_defaults(self, user_id):
        self._service.ensure_defaults(user_id)
        return Result(True)
