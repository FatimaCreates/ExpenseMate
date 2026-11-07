from constants import SUPPORTED_CURRENCIES
from controllers.result import Result
from services.user_service import UserService


class UserController:

    def __init__(self, service=None):
        self._service = service or UserService()

    def login(self, username, password):
        user = self._service.verify((username or "").strip(), password)
        if user:
            return Result(True, data=user)
        return Result(False, "Incorrect username or password.", error="invalid_credentials")

    def register(self, username, password, confirm_password, currency="PKR"):
        if not (username or "").strip() or not password:
            return Result(False, "Please fill in all fields.", error="validation")
        if password != confirm_password:
            return Result(False, "Passwords do not match.", error="validation")
        try:
            user_id = self._service.register(username.strip(), password, currency)
        except ValueError as exc:
            return Result(False, str(exc), error="validation")
        return Result(True, "Account created! Switch to Login to continue.", data=user_id)

    def change_currency(self, user_id, currency):
        if currency not in SUPPORTED_CURRENCIES:
            return Result(False, f"Unsupported currency '{currency}'.", error="validation")
        self._service.set_currency(user_id, currency)
        return Result(True)
