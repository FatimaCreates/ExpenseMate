"""
Unit tests for the Assignment 02 / Part B layers.

Services and controllers are tested with FAKE repositories, so no SQLite file
is touched: this is what the layered design buys us.
"""

from datetime import date, datetime

import pytest

from controllers import TransactionController, BudgetController
from services import BudgetService, TransactionService, BudgetExceededError
from services.validators import validate_date, validate_amount


# ----------------------------------------------------------------- fakes
class FakeTransactionRepo:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.added = []

    def add(self, user_id, date_, type_, category, amount, note=""):
        self.added.append((user_id, date_, type_, category, amount, note))

    def list_for_month(self, user_id, year_month):
        return [r for r in self.rows if r["date"].startswith(year_month)]

    def list_for_user(self, user_id):
        return list(self.rows)


class FakeBudgetRepo:
    def __init__(self, budgets=None):
        self.budgets = budgets or []
        self.saved = []

    def list_for_user(self, user_id):
        return list(self.budgets)

    def upsert(self, user_id, category, limit):
        self.saved.append((category, limit))


def txn(date_, type_, category, amount):
    return {"date": date_, "type": type_, "category": category, "amount": amount}


def make_budget_service(rows=(), budgets=()):
    return BudgetService(FakeTransactionRepo(list(rows)), FakeBudgetRepo(list(budgets)),
                         clock=lambda: datetime(2026, 10, 15))


# ------------------------------------------------------------ validators
def test_validate_date_normalises_and_rejects_future():
    assert validate_date("2026-3-5", today=date(2026, 11, 7)) == "2026-03-05"
    with pytest.raises(ValueError, match="future"):
        validate_date("2026-11-08", today=date(2026, 11, 7))
    with pytest.raises(ValueError, match="Invalid date"):
        validate_date("2026-02-30", today=date(2026, 11, 7))


def test_validate_amount_rejects_negative_and_none():
    assert validate_amount(0) == 0
    for bad in (-1, None):
        with pytest.raises(ValueError):
            validate_amount(bad)


# ----------------------------------------------------------- BudgetService
def test_monthly_summary_only_counts_requested_month():
    svc = make_budget_service(rows=[
        txn("2026-10-01", "income", "Salary", 1000),
        txn("2026-10-02", "expense", "Food", 300),
        txn("2026-09-02", "expense", "Food", 999),
    ])
    assert svc.monthly_summary(1, "2026-10") == {
        "total_income": 1000, "total_expense": 300, "net_balance": 700}


def test_default_month_comes_from_injected_clock():
    svc = make_budget_service(rows=[txn("2026-10-02", "expense", "Food", 50)])
    assert svc.monthly_summary(1)["total_expense"] == 50


def test_budget_report_has_progress_and_alerts_from_one_read():
    repo = FakeTransactionRepo([txn("2026-10-02", "expense", "Food", 1200),
                                txn("2026-10-03", "expense", "Rent", 100)])
    budgets = FakeBudgetRepo([{"category": "Food", "monthly_limit": 1000},
                              {"category": "Rent", "monthly_limit": 400}])
    report = BudgetService(repo, budgets).monthly_budget_report(1, "2026-10")
    assert report["category_totals"] == {"Food": 1200, "Rent": 100}
    assert report["alerts"] == [{"category": "Food", "spent": 1200, "limit": 1000, "over_by": 200}]
    assert {p["category"]: p["percent"] for p in report["progress"]} == {"Food": 120.0, "Rent": 25.0}


def test_zero_limit_gives_zero_percent_not_division_error():
    svc = make_budget_service(budgets=[{"category": "Food", "monthly_limit": 0}])
    assert svc.budget_progress(1, "2026-10")[0]["percent"] == 0


def test_would_exceed_budget_boundaries():
    svc = make_budget_service(rows=[txn("2026-10-02", "expense", "Food", 800)],
                              budgets=[{"category": "Food", "monthly_limit": 1000}])
    assert svc.would_exceed_budget(1, "Food", 200, "2026-10") is None            # exactly at limit
    assert svc.would_exceed_budget(1, "Food", 201, "2026-10")["over_by"] == 1    # one over
    assert svc.would_exceed_budget(1, "Transport", 9999, "2026-10") is None     # no budget set


def test_set_budget_rejects_negative_limit_before_touching_repo():
    budgets = FakeBudgetRepo()
    svc = BudgetService(FakeTransactionRepo(), budgets)
    with pytest.raises(ValueError):
        svc.set_budget(1, "Food", -5)
    assert budgets.saved == []


# ------------------------------------------------------ TransactionService
def make_tx_service(rows=(), budgets=()):
    tx_repo = FakeTransactionRepo(list(rows))
    budget_service = BudgetService(tx_repo, FakeBudgetRepo(list(budgets)))
    return TransactionService(tx_repo, budget_service), tx_repo


def test_add_transaction_saves_normalised_date():
    svc, repo = make_tx_service()
    svc.add_transaction(1, "2026-3-5", "expense", "Food", 10)
    assert repo.added == [(1, "2026-03-05", "expense", "Food", 10, "")]


def test_invalid_input_never_reaches_repository():
    svc, repo = make_tx_service()
    with pytest.raises(ValueError):
        svc.add_transaction(1, "2026-03-05", "expense", "Food", -1)
    with pytest.raises(ValueError):
        svc.add_transaction(1, "not-a-date", "expense", "Food", 1)
    assert repo.added == []


def test_budget_guard_blocks_expense_but_not_income():
    svc, repo = make_tx_service(
        rows=[txn("2026-10-02", "expense", "Food", 900)],
        budgets=[{"category": "Food", "monthly_limit": 1000}])
    with pytest.raises(BudgetExceededError) as err:
        svc.add_transaction(1, "2026-10-05", "expense", "Food", 200, enforce_budget=True)
    assert err.value.details["over_by"] == 100
    assert repo.added == []
    svc.add_transaction(1, "2026-10-05", "income", "Food", 5000, enforce_budget=True)
    assert len(repo.added) == 1


def test_budget_guard_is_opt_in():
    svc, repo = make_tx_service(
        rows=[txn("2026-10-02", "expense", "Food", 900)],
        budgets=[{"category": "Food", "monthly_limit": 1000}])
    svc.add_transaction(1, "2026-10-05", "expense", "Food", 200)   # legacy / CSV-import path
    assert len(repo.added) == 1


# ------------------------------------------------------------- controllers
def test_controller_rejects_empty_category_and_zero_amount_without_calling_service():
    class Boom:
        def add_transaction(self, *a, **k):
            raise AssertionError("service must not be called")
    ctl = TransactionController(Boom())
    assert ctl.add_transaction(1, "2026-10-05", "expense", "", 10).error == "validation"
    assert ctl.add_transaction(1, "2026-10-05", "expense", "Food", 0).error == "validation"


def test_controller_maps_budget_error_to_result_with_details():
    svc, _ = make_tx_service(rows=[txn("2026-10-02", "expense", "Food", 900)],
                             budgets=[{"category": "Food", "monthly_limit": 1000}])
    result = TransactionController(svc).add_transaction(1, "2026-10-05", "expense", "Food", 500)
    assert (result.ok, result.error) == (False, "budget_exceeded")
    assert result.data["limit"] == 1000


def test_budget_controller_validates_then_delegates():
    budgets = FakeBudgetRepo()
    ctl = BudgetController(BudgetService(FakeTransactionRepo(), budgets))
    assert ctl.set_budget(1, "Food", 0).ok is False
    assert ctl.set_budget(1, "Food", 500).ok is True
    assert budgets.saved == [("Food", 500)]


# =========================================================================
# Users / login, categories, savings goals (second half of Part B)
# =========================================================================
from controllers import UserController, CategoryController, SavingsController
from repositories.errors import DuplicateRecordError
from services import UserService, CategoryService, SavingsService
from services.security import hash_password


class FakeUserRepo:
    def __init__(self):
        self.users = {}

    def create(self, username, password_hash, currency):
        if username in self.users:
            raise DuplicateRecordError(username)
        self.users[username] = {"id": len(self.users) + 1, "username": username,
                                "password_hash": password_hash, "currency": currency}
        return self.users[username]["id"]

    def find_by_username(self, username):
        return self.users.get(username)

    def find_by_id(self, user_id):
        return next((u for u in self.users.values() if u["id"] == user_id), None)

    def update_currency(self, user_id, currency):
        self.find_by_id(user_id)["currency"] = currency


class FakeCategoryRepo:
    def __init__(self, names=None, used=()):
        self.names = list(names or [])
        self.used = set(used)

    def list_names(self, user_id):
        return sorted(self.names, key=str.lower)

    def add(self, user_id, name):
        if name in self.names:
            raise DuplicateRecordError(name)
        self.names.append(name)

    def add_many_ignoring_duplicates(self, user_id, names):
        for n in names:
            if n not in self.names:
                self.names.append(n)

    def find_id(self, user_id, name):
        return self.names.index(name) + 1 if name in self.names else None

    def usage_count(self, category_id):
        return 1 if self.names[category_id - 1] in self.used else 0

    def delete(self, user_id, name):
        self.names.remove(name)


class FakeGoalRepo:
    def __init__(self, goals=()):
        self.goals = list(goals)

    def list_for_user(self, user_id):
        return list(self.goals)

    def add(self, user_id, name, target):
        self.goals.append({"id": len(self.goals) + 1, "name": name,
                           "target_amount": target, "saved_amount": 0})

    def update_saved(self, goal_id, saved):
        next(g for g in self.goals if g["id"] == goal_id)["saved_amount"] = saved


def test_register_hashes_password_and_seeds_default_categories():
    users, cats = FakeUserRepo(), FakeCategoryRepo()
    uid = UserService(users, cats).register("  sara ", "secret")
    assert users.users["sara"]["password_hash"] == hash_password("secret") != "secret"
    assert "Food" in cats.names and uid == 1


def test_register_rejects_empty_and_duplicate():
    svc = UserService(FakeUserRepo(), FakeCategoryRepo())
    with pytest.raises(ValueError, match="Username cannot be empty"):
        svc.register("  ", "pw")
    with pytest.raises(ValueError, match="Password cannot be empty"):
        svc.register("sara", "")
    svc.register("sara", "pw")
    with pytest.raises(ValueError, match="already exists"):
        svc.register("sara", "pw2")


def test_unsupported_currency_falls_back_to_pkr_on_register_but_raises_on_change():
    users = FakeUserRepo()
    svc = UserService(users, FakeCategoryRepo())
    svc.register("sara", "pw", currency="XXX")
    assert users.users["sara"]["currency"] == "PKR"
    with pytest.raises(ValueError):
        svc.set_currency(1, "XXX")


def test_verify_accepts_right_password_only():
    svc = UserService(FakeUserRepo(), FakeCategoryRepo())
    svc.register("sara", "pw")
    assert svc.verify("sara", "pw")["username"] == "sara"
    assert svc.verify("sara", "wrong") is None
    assert svc.verify("nobody", "pw") is None


def test_user_controller_checks_fields_before_calling_service():
    ctl = UserController(UserService(FakeUserRepo(), FakeCategoryRepo()))
    assert ctl.register("", "pw", "pw").message == "Please fill in all fields."
    assert ctl.register("sara", "pw", "other").message == "Passwords do not match."
    assert ctl.register("sara", "pw", "pw").ok
    assert ctl.login(" sara ", "pw").ok                       # username is stripped
    assert ctl.login("sara", "bad").error == "invalid_credentials"
    assert ctl.change_currency(1, "XXX").ok is False


def test_category_add_rejects_case_insensitive_duplicates_and_empty():
    svc = CategoryService(FakeCategoryRepo(["Food"]))
    with pytest.raises(ValueError, match="already exists"):
        svc.add_category(1, " food ")
    with pytest.raises(ValueError, match="empty"):
        svc.add_category(1, "  ")
    assert svc.add_category(1, " Gym ") == "Gym"


def test_category_in_use_cannot_be_deleted_but_unused_can():
    repo = FakeCategoryRepo(["Food", "Gym"], used={"Food"})
    svc = CategoryService(repo)
    with pytest.raises(ValueError, match="used by"):
        svc.delete_category(1, "Food")
    svc.delete_category(1, "Gym")
    assert repo.names == ["Food"]


def test_ensure_defaults_adds_only_missing_ones():
    repo = FakeCategoryRepo(["food"])                         # different case counts as present
    CategoryService(repo).ensure_defaults(1)
    assert repo.names.count("food") == 1 and "Food" not in repo.names and "Rent" in repo.names


def test_category_controller_empty_name_never_reaches_service():
    class Boom:
        def add_category(self, *a):
            raise AssertionError("service must not be called")
    assert CategoryController(Boom()).add_category(1, "  ").error == "validation"


def test_savings_progress_percent_is_capped_and_safe_for_zero_target():
    svc = SavingsService(FakeGoalRepo([
        {"id": 1, "name": "A", "target_amount": 200, "saved_amount": 50},
        {"id": 2, "name": "B", "target_amount": 100, "saved_amount": 250},
        {"id": 3, "name": "C", "target_amount": 0, "saved_amount": 10},
    ]))
    assert [g["percent"] for g in svc.goals_progress(1)] == [25.0, 100, 0]


def test_savings_controller_validates_then_delegates():
    repo = FakeGoalRepo()
    ctl = SavingsController(SavingsService(repo))
    assert ctl.add_goal(1, "", 100).ok is False
    assert ctl.add_goal(1, "Trip", 0).ok is False
    assert ctl.add_goal(1, " Trip ", 500).ok
    assert ctl.update_progress(1, 120).ok
    assert repo.goals[0]["name"] == "Trip" and repo.goals[0]["saved_amount"] == 120
