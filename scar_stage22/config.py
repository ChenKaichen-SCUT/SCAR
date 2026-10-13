from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'results/stage22'
REPORTS = ROOT / 'reports/stage22'
ENGINE = Path(os.environ.get('AGENTODYSSEY_ROOT', '/mnt/Space0/scar_dependencies/agentodyssey_stage22'))
ENGINE_COMMIT = '248430692a9d4a61d38c6c03ab2126287faaf450'
STAGE18_COMMIT = '2c2f7ecc03b0e326f26cdf85ce13e2415b374e33'
GAMES = ('remnant', 'mark', 'metropolis')
METHODS = ('Stage18-Fixed', 'NoMemoryAgent', 'ShortTermMemoryAgent', 'LongContextAgent', 'VoyagerAgent')
AGENT_ID = 'agent_adam_davis'
MAX_STEPS = 300
SEED = 42
EMBEDDING_REVISION = '97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3'
EMBEDDING_PATH = str(Path('/root/.cache/huggingface/hub/models--Qwen--Qwen3-Embedding-0.6B/snapshots') / EMBEDDING_REVISION)
MODEL = dict(model='deepseek-flash', base_url='https://api.deepseek.com',
             temperature=0.7, top_p=0.8, presence_penalty=1.5,
             thinking='disabled', max_tokens=768, context_window=1000000,
             response_format={'type': 'json_object'}, retries=3,
             peak_prices=dict(cache_hit=0.006, cache_miss=0.3, output=1.2),
             off_peak_multiplier=0.5, total_budget_usd=100, episode_budget_usd=25)
# Resource safeguards, not a $100 spending target. At most 4,500 actions and
# approximately 6,300 requests; large LongContext prompts dominate the estimate.
SCHEDULE = [(g, 'VoyagerAgent') for g in GAMES] + [(g, m) for g in GAMES for m in METHODS if m != 'VoyagerAgent']
