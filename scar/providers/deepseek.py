"""OpenAI-compatible provider with shared budget, concurrency and request auditing."""
import contextlib
import fcntl
import json
import os
from pathlib import Path
import random
import re
import sqlite3
import time
import uuid

from scar.io import append_jsonl


class BudgetExceeded(RuntimeError):
    pass


class EpisodeBudgetExceeded(BudgetExceeded):
    pass


class ModelResponseError(RuntimeError):
    pass


def read_key(path=None):
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not key:
        if not path:
            raise ValueError("DEEPSEEK_API_KEY or a key file is required")
        path = Path(path)
        path.chmod(0o600)
        raw = path.read_text().strip()
        if raw.startswith("{"):
            data = json.loads(raw)
            key = data.get("DEEPSEEK_API_KEY", data.get("api_key", ""))
        elif re.fullmatch(r"(?:export\s+)?DEEPSEEK_API_KEY\s*=.*", raw):
            key = raw.split("=", 1)[1].strip().strip("\"'")
        else:
            key = raw
    if not isinstance(key, str) or not re.fullmatch(r"sk-[A-Za-z0-9_-]{16,}", key):
        raise ValueError("Key file format not recognized; content is not logged")
    return key


class BudgetLedger:
    """Reservation prevents concurrent workers from collectively overspending."""
    def __init__(self, path, limit):
        self.path, self.limit = str(path), float(limit)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, reserved REAL, charged REAL, status TEXT)")

    def connect(self):
        return sqlite3.connect(self.path, timeout=60)

    def reserve(self, request_id, upper):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            spent = db.execute("SELECT COALESCE(SUM(COALESCE(charged,reserved)),0) FROM requests").fetchone()[0]
            if spent + upper > self.limit:
                raise BudgetExceeded(f"Budget cap ${self.limit:.2f}; committed ${spent:.6f}, next reserve ${upper:.6f}")
            db.execute("INSERT INTO requests VALUES (?,?,NULL,'reserved')", (request_id, upper))

    def settle(self, request_id, charged, status):
        with self.connect() as db:
            db.execute("UPDATE requests SET charged=?,status=? WHERE id=?", (charged, status, request_id))

    def total(self):
        with self.connect() as db:
            return db.execute("SELECT COALESCE(SUM(COALESCE(charged,reserved)),0) FROM requests").fetchone()[0]


@contextlib.contextmanager
def concurrency_slot(directory, maximum, timeout=300):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    handle = None
    while handle is None:
        # flock locks are released automatically if a worker dies.
        for i in range(maximum):
            candidate = (directory / f"slot-{i}.lock").open("a+")
            try:
                fcntl.flock(candidate, fcntl.LOCK_EX | fcntl.LOCK_NB)
                handle = candidate
                break
            except BlockingIOError:
                candidate.close()
        if handle is None:
            if time.monotonic() - start > timeout:
                raise TimeoutError("API concurrency queue timed out")
            time.sleep(0.1)
    try:
        yield
    finally:
        fcntl.flock(handle, fcntl.LOCK_UN)
        handle.close()


def estimate_cost(usage, prices):
    inputs = usage.get("prompt_tokens", 0)
    outputs = usage.get("completion_tokens", 0)
    hits = usage.get("prompt_cache_hit_tokens", usage.get("prompt_tokens_details", {}).get("cached_tokens", 0))
    return (hits * prices["cache_hit"] + (inputs - hits) * prices["cache_miss"] + outputs * prices["output"]) / 1e6


class DeepSeekProvider:
    def __init__(self, config, audit_path, ledger_path, key_path=None, max_concurrency=4):
        from openai import OpenAI
        self.config = config
        self.audit_path = Path(audit_path)
        self.ledger = BudgetLedger(ledger_path, config["total_budget_usd"])
        self.slots = Path(ledger_path).parent / "api_slots"
        self.maximum = max_concurrency
        self.episode_ledger = (BudgetLedger(self.audit_path.parent / "episode_budget.sqlite", config["episode_budget_usd"])
                               if config.get("episode_budget_usd") is not None else None)
        self.client = OpenAI(api_key=read_key(key_path), base_url=config["base_url"], timeout=90, max_retries=0)
        self.tokens_in = self.tokens_out = self.calls = self.failures = 0
        self.cost = self.latency = 0.0

    def generate(self, user_prompt, system_prompt=None, required=("action", "reasoning")):
        messages = ([{"role": "system", "content": system_prompt}] if system_prompt else [])
        messages.append({"role": "user", "content": user_prompt})
        prices = self.config["pricing_usd_per_million"]
        # UTF-8 bytes upper-bound ordinary text tokens; overhead reserved conservatively.
        upper = ((len(json.dumps(messages, ensure_ascii=False).encode()) + 1024) * prices["cache_miss"]
                 + self.config["max_tokens"] * prices["output"]) / 1e6
        last_error = None
        for attempt in range(3):
            request_id = uuid.uuid4().hex
            self.ledger.reserve(request_id, upper)
            if self.episode_ledger:
                try:
                    self.episode_ledger.reserve(request_id, upper)
                except BudgetExceeded as exc:
                    self.ledger.settle(request_id, 0, "episode_budget_stop_before_request")
                    raise EpisodeBudgetExceeded(str(exc)) from None
            start = time.time()
            record = {"request_id": request_id, "attempt": attempt, "start": start,
                      "model": self.config["model"], "thinking": self.config["thinking"],
                      "messages": messages, "reserved_usd": upper}
            charged, status = upper, "unknown_billing"
            try:
                with concurrency_slot(self.slots, self.maximum):
                    response = self.client.chat.completions.create(
                        model=self.config["model"], messages=messages,
                        temperature=self.config["temperature"], max_tokens=self.config["max_tokens"],
                        response_format={"type": "json_object"},
                        extra_body={"thinking": {"type": self.config["thinking"]}},
                    )
                raw = response.model_dump()
                usage = raw.get("usage")
                if not isinstance(usage, dict) or "prompt_tokens" not in usage or "completion_tokens" not in usage:
                    raise ModelResponseError("Missing auditable token usage")
                content = raw["choices"][0]["message"]["content"]
                charged = estimate_cost(usage, prices)
                self.tokens_in += usage["prompt_tokens"]
                self.tokens_out += usage["completion_tokens"]
                self.cost += charged
                record.update(raw_response=raw, usage=usage, cost_usd=charged)
                parsed = json.loads(content)
                if not isinstance(parsed, dict) or not all(k in parsed for k in required):
                    raise ModelResponseError("Required JSON fields missing")
                if "action" in required and (not isinstance(parsed["action"], str) or not parsed["action"].strip()):
                    raise ModelResponseError("Action is not a nonempty string")
                status = "ok"
                return {"response": content, "num_input_tokens": usage["prompt_tokens"],
                        "num_output_tokens": usage["completion_tokens"], "raw": raw,
                        "usage": usage, "cost_usd": charged, "parsed": parsed}
            except Exception as exc:
                self.failures += 1
                last_error = type(exc).__name__
                code = getattr(exc, "status_code", None)
                record.update(error_type=last_error, http_status=code)
                if code is not None and 400 <= code < 500:
                    charged, status = 0.0, "rejected"
                elif "usage" in record:
                    status = "invalid_response"
                if code in {400, 401, 402, 403, 404, 422}:
                    raise RuntimeError(f"DeepSeek request rejected: HTTP {code}; see sanitized audit") from None
            finally:
                elapsed = time.time() - start
                self.calls += 1
                self.latency += elapsed
                self.ledger.settle(request_id, charged, status)
                if self.episode_ledger:
                    self.episode_ledger.settle(request_id, charged, status)
                record.update(end=time.time(), latency_seconds=elapsed, status=status, charged_or_reserved_usd=charged)
                append_jsonl(self.audit_path, record)
            if attempt < 2:
                time.sleep(2 ** attempt + random.SystemRandom().random())
        raise ModelResponseError(f"Three request/parse attempts failed ({last_error}); no game action executed")

    def totals(self):
        return {"input_tokens": self.tokens_in, "output_tokens": self.tokens_out,
                "api_calls": self.calls, "failed_requests": self.failures,
                "cost_usd": self.cost, "api_latency_seconds": self.latency}
