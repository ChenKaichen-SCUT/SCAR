"""Audited DeepSeek transport. Credentials stay outside source and checkpoints."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import time
import uuid

import requests

from scar.io import atomic_json, append_jsonl


def read_key(path):
    candidates = re.findall(r"sk-[A-Za-z0-9_-]+", Path(path).read_text(encoding="utf-8-sig"))
    if len(set(candidates)) != 1:
        raise ValueError("Key file must contain exactly one distinct API key")
    return candidates[0]


def peak_cost(usage):
    hit = usage.get("prompt_cache_hit_tokens", 0)
    total = usage.get("prompt_tokens", 0)
    return (hit * .006 + max(0, total - hit) * .30 + usage.get("completion_tokens", 0) * 1.20) / 1e6


class Provider:
    def __init__(self, directory, key_path, model="deepseek-flash", base="https://api.deepseek.com"):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.key_path, self.model, self.base = str(key_path), model, base.rstrip("/")
        self.session = requests.Session()
        self.session.trust_env = False
        self.step = 0
        self.last = None

    def request(self, messages, repair=0):
        payload = {"model": self.model, "messages": messages, "temperature": .7,
                   "top_p": .8, "presence_penalty": 0, "max_tokens": 1536,
                   "thinking": {"type": "disabled"}, "response_format": {"type": "json_object"}}
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
        digest = hashlib.sha256(encoded).hexdigest()
        # Step-specific: identical prompts at two different steps remain independent draws.
        prefix = self.directory / f"{self.step:04d}-{repair}-{digest[:16]}"
        cache = prefix.with_suffix(".response.json")
        if cache.exists():
            result = json.loads(cache.read_text())
            append_jsonl(self.directory / "reuse.jsonl", {"step": self.step, "request_hash": digest})
            return result
        with gzip.open(prefix.with_suffix(".request.json.gz"), "wb") as f:
            f.write(encoded)
        key = read_key(self.key_path)
        for attempt in range(4):
            uid = uuid.uuid4().hex
            start = time.time()
            record = {"id": uid, "step": self.step, "repair": repair, "attempt": attempt,
                      "request_hash": digest, "started_utc": start, "requested_model": self.model}
            append_jsonl(self.directory / "attempts.jsonl", {**record, "event": "started"})
            try:
                response = self.session.post(self.base + "/chat/completions", json=payload,
                    headers={"Authorization": "Bearer " + key}, timeout=(20, 180))
                record.update(status=response.status_code, elapsed_s=time.time() - start)
                if response.status_code != 200:
                    # Do not echo arbitrary server error bodies or request headers.
                    record.update(event="http_error", charge_unknown=response.status_code >= 500)
                    append_jsonl(self.directory / "attempts.jsonl", record)
                    if response.status_code not in (408, 429, 500, 502, 503, 504):
                        raise RuntimeError(f"API HTTP {response.status_code}; see sanitized audit")
                    time.sleep(min(2 ** (attempt + 1), 16))
                    continue
                result = response.json()
                usage = result.get("usage", {})
                record.update(event="completed", usage=usage, actual_model=result.get("model"),
                              peak_usd=peak_cost(usage), charge_unknown=not bool(usage))
                append_jsonl(self.directory / "attempts.jsonl", record)
                atomic_json(cache, result)
                return result
            except (requests.RequestException, ValueError) as exc:
                record.update(event="transport_error", error_type=type(exc).__name__,
                              elapsed_s=time.time()-start, charge_unknown=True)
                append_jsonl(self.directory / "attempts.jsonl", record)
                time.sleep(min(2 ** (attempt + 1), 16))
        raise RuntimeError("API retries exhausted; resume reuses completed requests")

    def generate(self, user_prompt, system_prompt):
        messages = [{"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}]
        for repair in range(6):
            result = self.request(messages, repair)
            choice = result["choices"][0]
            raw = choice["message"].get("content", "")
            try:
                parsed = json.loads(raw)
                if not isinstance(parsed, dict) or not isinstance(parsed.get("reasoning"), str):
                    raise ValueError("reasoning must be a string")
                if not isinstance(parsed.get("action"), str) or not parsed["action"].strip():
                    raise ValueError("action must be a nonempty string")
                if choice.get("finish_reason") == "length":
                    raise ValueError("truncated output")
                self.last = parsed
                usage = result.get("usage", {})
                return {"response": raw, "num_input_tokens": usage.get("prompt_tokens", 0),
                        "num_output_tokens": usage.get("completion_tokens", 0)}
            except (ValueError, TypeError):
                # Common JSON-only repair. No environment feedback or semantic action repair.
                correction = (
                    "Your output was malformed or truncated. Return a complete JSON object with string "
                    "reasoning and action fields. Keep it concise. Follow the original schema.")
                if repair >= 2:
                    correction += (' The action key is mandatory, separate from reasoning. '
                        'Required shape: {"reasoning":"brief explanation","action":"one game command"}. '
                        'Include both keys. Keep any additional fields required by the original schema.')
                messages += [{"role": "assistant", "content": raw}, {"role": "user", "content": correction}]
        raise RuntimeError("Six invalid model outputs; no silent wait action")


def usage_summary(directory):
    rows = []
    for path in Path(directory).rglob("attempts.jsonl"):
        rows += [json.loads(line) for line in path.read_text().splitlines() if line]
    started = {r["id"] for r in rows if r["event"] == "started"}
    ended = {r["id"] for r in rows if r["event"] != "started"}
    complete = [r for r in rows if r["event"] == "completed"]
    return {"requests": len(started), "successful_responses": len(complete),
            "peak_usd_estimate": sum(r.get("peak_usd", 0) for r in complete),
            "unknown_charge_attempts": sum(bool(r.get("charge_unknown")) for r in rows) + len(started-ended),
            "prompt_tokens": sum(r.get("usage", {}).get("prompt_tokens", 0) for r in complete),
            "completion_tokens": sum(r.get("usage", {}).get("completion_tokens", 0) for r in complete)}
