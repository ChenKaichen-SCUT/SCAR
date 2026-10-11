"""V3 budget authorization adapter; original provider/accounting stays frozen."""
from scar.providers.deepseek import DeepSeekProvider, BudgetLedger


def authorized_limit(config):
    limit = config.get("total_budget_usd")
    if limit is None:
        if config.get("budget_authorization") != "user_waived_20_usd_cap_for_required_v3_cohort":
            raise ValueError("Uncapped accounting requires recorded authorization for this cohort")
        return float("inf")  # In-memory ledger comparison only; never serialized.
    return float(limit)


def ledger_for(path, config):
    return BudgetLedger(path, authorized_limit(config))


class CohortProvider(DeepSeekProvider):
    def __init__(self, config, *args, **kwargs):
        super().__init__(dict(config, total_budget_usd=authorized_limit(config)), *args, **kwargs)
        self.config = config  # Saved configuration uses JSON null, not Infinity.
