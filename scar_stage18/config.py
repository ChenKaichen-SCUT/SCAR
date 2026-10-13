"""Protocol constants. Freeze before the first formal request."""
from scar_stage17.provider import CONFIG as STAGE17_PROVIDER

METHOD = 'SCAR18'
PROVIDER = dict(STAGE17_PROVIDER, total_budget_usd=3.0, episode_budget_usd=0.25)
MAX_ACTIONS = 100
UNKNOWN_ACQUISITION = 1
SUMMARY_RECORDS = 48
SUMMARY_CHARACTERS = 6000
STAGE16_COMMIT = '1b650b41dea958d22e8415d8b23770f2454a8028'
STAGE17_COMMIT = 'ab6faaa21dda4073dd52c920ca6a705e75a93e3a'
