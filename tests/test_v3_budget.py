"""Budget authorization changes accounting limits, never resets historical spend."""
import pytest
from scar.providers.deepseek import BudgetExceeded
from scar_v3.provider import ledger_for, authorized_limit


def test_explicit_waiver_retains_existing_charges(tmp_path):
    path = tmp_path/"budget.sqlite"
    old = ledger_for(path, {"total_budget_usd":20})
    old.reserve("old", 19.9); old.settle("old", 19.9, "ok")
    with pytest.raises(BudgetExceeded):
        old.reserve("over", .2)
    new = ledger_for(path, {"total_budget_usd":None,
        "budget_authorization":"user_waived_20_usd_cap_for_required_v3_cohort"})
    new.reserve("new", .2); new.settle("new", .2, "ok")
    assert new.total() == pytest.approx(20.1)


def test_missing_cap_without_authorization_is_not_silently_unlimited():
    with pytest.raises(ValueError):
        authorized_limit({"total_budget_usd":None})
