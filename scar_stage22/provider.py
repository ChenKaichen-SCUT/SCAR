"""Shared raw-response transport; official parsers keep their native behavior.

Never resample a paid response because a decision looks bad or parses badly.
Cache exact requests to resume infrastructure interruptions without new samples.
All Voyager calls (including distillation omitted by its return token counters)
are recorded here. Unknown billing aborts; no blind timeout resampling.
"""
import datetime as dt
import json
import time
from pathlib import Path
from scar.io import append_jsonl, atomic_json, digest
from scar.providers.deepseek import BudgetLedger, estimate_cost, read_key, concurrency_slot
from .config import MODEL


def prices_at(timestamp):
    utc = dt.datetime.fromtimestamp(timestamp, dt.timezone.utc)
    # These runs are on 2026-10-13 (not a Chinese public holiday).
    peak = utc.weekday() < 5 and (1 <= utc.hour < 4 or 6 <= utc.hour < 10)
    factor = 1 if peak else MODEL['off_peak_multiplier']
    return {k: v * factor for k, v in MODEL['peak_prices'].items()}


def role(system):
    if 'automatic curriculum agent' in system: return 'curriculum'
    if 'judge whether the current task' in system: return 'critic'
    if 'skill distillation assistant' in system: return 'skill_distillation'
    return 'action'


class Provider:
    def __init__(self, folder, runtime, key):
        from openai import OpenAI
        self.folder = Path(folder)
        self.audit = self.folder / 'requests.jsonl'
        self.pending = self.folder / 'pending_request.json'
        self.ledger = BudgetLedger(Path(runtime) / 'budget.sqlite', MODEL['total_budget_usd'])
        self.episode = BudgetLedger(self.folder / 'budget.sqlite', MODEL['episode_budget_usd'])
        self.slots = Path(runtime) / 'api_slots'
        self.client = OpenAI(api_key=read_key(key), base_url=MODEL['base_url'], timeout=120, max_retries=0)
        self.cache = {}
        if self.audit.exists():
            for line in self.audit.read_text().splitlines():
                row = json.loads(line)
                if row['status'] == 'ok': self.cache[row['logical_id']] = row
        if self.pending.exists():
            raise RuntimeError('Unresolved pending request: preserve checkpoint and billing evidence')
        self.begin_step(0)

    def begin_step(self, step):
        self.step, self.ordinal = step, 0

    def generate(self, user_prompt, system_prompt=None, **kwargs):
        self.ordinal += 1
        logical = f'{self.step:03d}:{self.ordinal:03d}'
        messages = ([dict(role='system', content=system_prompt)] if system_prompt else []) + [dict(role='user', content=user_prompt)]
        signature = digest(messages)
        if logical in self.cache:
            row = self.cache[logical]
            assert signature == row['signature'], 'Resume must preserve the frozen request'
            return self.result(row)
        upper = ((len(json.dumps(messages, ensure_ascii=False).encode()) + 1024) * MODEL['peak_prices']['cache_miss'] + MODEL['max_tokens'] * MODEL['peak_prices']['output']) / 1e6
        for attempt in range(MODEL['retries']):
            ident = digest([str(self.folder), logical, attempt])
            self.ledger.reserve(ident, upper)
            try: self.episode.reserve(ident, upper)
            except Exception:
                self.ledger.settle(ident, 0, 'episode_budget_abort')
                raise
            row = dict(request_id=ident, logical_id=logical, step=self.step, ordinal=self.ordinal,
                       phase=role(system_prompt or ''), attempt=attempt, signature=signature,
                       messages=messages, start=time.time(), model=MODEL['model'],
                       temperature=MODEL['temperature'], top_p=MODEL['top_p'],
                       presence_penalty=MODEL['presence_penalty'], thinking=MODEL['thinking'],
                       max_tokens=MODEL['max_tokens'], reserved_usd=upper)
            atomic_json(self.pending, dict(request_id=ident, logical_id=logical))
            charged, status, retry = upper, 'unknown_billing', False
            try:
                with concurrency_slot(self.slots, 12):
                    response = self.client.chat.completions.create(
                        model=MODEL['model'], messages=messages,
                        temperature=MODEL['temperature'], top_p=MODEL['top_p'],
                        presence_penalty=MODEL['presence_penalty'], max_tokens=MODEL['max_tokens'],
                        response_format=MODEL['response_format'],
                        extra_body={'thinking': {'type': MODEL['thinking']}})
                raw = response.model_dump()
                row['raw_response'] = raw
                usage = raw.get('usage')
                if not usage or 'prompt_tokens' not in usage:
                    raise RuntimeError('API response has no billable usage')
                row['usage'] = usage
                row['unit_prices'] = prices_at(raw.get('created') or row['start'])
                charged = estimate_cost(usage, row['unit_prices'])
                row['cost_usd'] = charged
                row['peak_rate_reference_cost_usd'] = estimate_cost(usage, MODEL['peak_prices'])
                # Do not repair, reject, truncate or retry malformed model JSON.
                try: row['parsed_json'] = json.loads(raw['choices'][0]['message']['content'])
                except (ValueError, TypeError): row['parse_exception'] = 'invalid_json'
                status = 'ok'
            except Exception as exc:
                code = getattr(exc, 'status_code', None)
                row.update(error_type=type(exc).__name__, http_status=code)
                if code is not None and 400 <= code < 500:
                    charged, status = 0, 'http_rejected'
                    retry = code == 429
            finally:
                row.update(status=status, end=time.time(), charged_or_reserved_usd=charged)
                self.ledger.settle(ident, charged, status)
                self.episode.settle(ident, charged, status)
                append_jsonl(self.audit, row)
                if status != 'unknown_billing': self.pending.unlink()
            if status == 'ok':
                self.cache[logical] = row
                return self.result(row)
            if not retry or attempt == MODEL['retries'] - 1:
                raise RuntimeError('Transport abort: ' + status + '; billing and trajectory retained')
            time.sleep(2 ** attempt)

    @staticmethod
    def result(row):
        return dict(response=row['raw_response']['choices'][0]['message']['content'],
                    num_input_tokens=row['usage']['prompt_tokens'],
                    num_output_tokens=row['usage']['completion_tokens'])
