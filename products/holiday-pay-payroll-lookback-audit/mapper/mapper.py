"""map_names(rows, client): batch names, validate the reply strictly, never repair it.

A reply that is malformed, or leaves an id out, repeats an id or uses a category outside the nine, makes those rows
"UNMAPPED". They count as wrong in scoring. There are no retries with a changed prompt (kill-test rule). The only
retry is the transport's: same request again after a network error, 429 or 5xx.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

if __package__ in (None, ""):
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mapper.prompt import CATEGORIES, SYSTEM_PROMPT, build_user_message

UNMAPPED = "UNMAPPED"
DEFAULT_BATCH_SIZE = 200
MAX_OUTPUT_TOKENS = 16000  # reasoning tokens count inside this on gpt-5-mini; 200 answers need only ~4,000


class ClientError(Exception):
    """A transport or API failure with a message that never contains a key."""


@dataclass
class Completion:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class MapResult:
    predictions: dict[str, str]
    input_tokens: int = 0
    output_tokens: int = 0
    requests: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def unmapped(self) -> int:
        return sum(1 for v in self.predictions.values() if v == UNMAPPED)


def validate_reply(text: str, expected_ids: list[str]) -> tuple[dict[str, str], list[str]]:
    """(id -> category for every expected id, problems). Anything not valid is UNMAPPED, never fixed."""
    result = {i: UNMAPPED for i in expected_ids}
    problems: list[str] = []
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        return result, ["reply is not valid JSON"]
    if not isinstance(data, list):
        return result, ["reply is not a JSON array"]
    seen: dict[str, int] = {}
    cats: dict[str, str] = {}
    for item in data:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            problems.append("an item has no string id")
            continue
        seen[item["id"]] = seen.get(item["id"], 0) + 1
        cats[item["id"]] = item.get("category")
    expected = set(expected_ids)
    extra = sorted(set(seen) - expected)
    if extra:
        problems.append(f"{len(extra)} unknown id(s) returned, ignored")
    for i in expected_ids:
        n = seen.get(i, 0)
        if n == 0:
            problems.append(f"id {i} missing")
        elif n > 1:
            problems.append(f"id {i} returned {n} times")
        elif cats[i] not in CATEGORIES:
            problems.append(f"id {i} has invalid category {cats[i]!r}")
        else:
            result[i] = cats[i]
    return result, problems


def map_names(rows: list[dict], client, batch_size: int = DEFAULT_BATCH_SIZE) -> MapResult:
    ids = [r["id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("input ids are not unique")
    out = MapResult(predictions={})
    for start in range(0, len(rows), batch_size):
        batch = rows[start:start + batch_size]
        batch_ids = [r["id"] for r in batch]
        out.requests += 1
        try:
            completion = client.complete(SYSTEM_PROMPT, build_user_message(batch))
        except ClientError as error:
            out.errors.append(f"batch {out.requests}: {error}")
            out.predictions.update({i: UNMAPPED for i in batch_ids})
            continue
        out.input_tokens += completion.input_tokens
        out.output_tokens += completion.output_tokens
        preds, problems = validate_reply(completion.text, batch_ids)
        out.predictions.update(preds)
        out.errors.extend(f"batch {out.requests}: {p}" for p in problems)
    return out


# ---- clients ----

_KEYWORDS = (  # order matters: first match wins. Deterministic baseline only; not a quality claim.
    ("deduction_excluded", ("paye", "income tax", "national insurance", "nic", " ni ", "pension", "student loan",
                            "net pay", "deduction", "union", "attachment", "salary sacrifice", "tax")),
    ("holiday_pay_paid", ("holiday", "annual leave", "hol pay", "bank hol")),
    ("statutory_excluded", ("ssp", "smp", "spp", "shpp", "sap", "statutory", "sick pay", "maternity", "paternity")),
    ("regular_overtime", ("overtime", " ot", "extra hours")),
    ("commission", ("commission", "comm ", "sales incentive")),
    ("bonus_non_regular", ("bonus", "ex gratia", "ex-gratia", "golden")),
    ("expense_excluded", ("expense", "mileage", "travel", "subsistence", "reimburs", "benefit", "redundancy")),
    ("allowance", ("allowance", "weighting", "on call", "on-call", "standby", "shift")),
    ("basic", ("salary", "basic", "wage", "hourly", "regular pay", "standard pay")),
)


class FakeClient:
    """Deterministic keyword baseline. Makes no network call. Builds its answer from the user message only."""
    name = "fake"
    deployment = "fake"

    def complete(self, system: str, user: str) -> Completion:
        items = json.loads(user.split("\n", 1)[1])
        answer = []
        for item in items:
            text = " " + re.sub(r"[^a-z0-9 -]", " ", item["pay_element_name"].lower()) + " "
            cat = next((c for c, keys in _KEYWORDS if any(k in text for k in keys)), "basic")
            answer.append({"id": item["id"], "category": cat})
        return Completion(json.dumps(answer), len(system) // 4 + len(user) // 4, len(json.dumps(answer)) // 4)


def _normalise_endpoint(endpoint: str) -> str:
    root = endpoint.strip().rstrip("/")
    if "?" in root or "#" in root:
        raise ValueError("AZURE_OPENAI_ENDPOINT must not contain a query string or fragment")
    for suffix in ("/openai/v1/chat/completions", "/openai/v1/responses", "/openai/v1", "/openai"):
        if root.lower().endswith(suffix):
            return root[: -len(suffix)].rstrip("/")
    return root


class AzureOpenAIClient:
    """Azure OpenAI v1 API over urllib, same URL/auth pattern as products/_starter/backend/app/ai.py.

    api "auto": Responses when the endpoint ends in /openai/v1/responses, else chat completions.
    No temperature (gpt-5-mini rejects it). The key goes only in the api-key header and is never logged.
    """
    name = "azure"

    def __init__(self, endpoint: str, deployment: str = "gpt-5-mini", api_key: str = "", api: str = "auto",
                 timeout: float = 180.0, retries: int = 2, sleep=time.sleep, opener=None,
                 max_output_tokens: int = MAX_OUTPUT_TOKENS):
        if not endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT is not set")
        if api == "auto":
            api = "responses" if endpoint.strip().rstrip("/").lower().endswith("/openai/v1/responses") else "chat"
        if api not in ("chat", "responses"):
            raise ValueError("AZURE_OPENAI_API must be auto, chat or responses")
        self.api, self.deployment = api, deployment
        self.url = _normalise_endpoint(endpoint) + (
            "/openai/v1/responses" if api == "responses" else "/openai/v1/chat/completions")
        self._headers = {"api-key": api_key or "proxy-injected", "Content-Type": "application/json"}
        self.timeout, self.retries, self.sleep = timeout, retries, sleep
        self.opener = opener or urllib.request.urlopen
        self.max_output_tokens = max_output_tokens
        self.reported_model = ""

    @classmethod
    def from_env(cls, env=None) -> "AzureOpenAIClient":
        env = os.environ if env is None else env
        return cls(env.get("AZURE_OPENAI_ENDPOINT", ""), env.get("AZURE_OPENAI_DEPLOYMENT") or "gpt-5-mini",
                   env.get("AZURE_OPENAI_API_KEY", ""), env.get("AZURE_OPENAI_API") or "auto")

    def _payload(self, system: str, user: str) -> dict:
        if self.api == "responses":
            return {"model": self.deployment, "instructions": system, "max_output_tokens": self.max_output_tokens,
                    "store": False, "input": [{"role": "user", "content": user}]}
        return {"model": self.deployment, "max_completion_tokens": self.max_output_tokens,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}

    def complete(self, system: str, user: str) -> Completion:
        body = json.dumps(self._payload(system, user)).encode("utf-8")
        last = "unknown error"
        for attempt in range(self.retries + 1):
            if attempt:
                self.sleep(min(2 ** attempt, 20))  # same request again: backoff 2s, 4s
            request = urllib.request.Request(self.url, data=body, headers=self._headers, method="POST")
            try:
                with self.opener(request, timeout=self.timeout) as response:
                    raw = response.read()
            except urllib.error.HTTPError as error:
                last = f"HTTP {error.code}"
                if error.code == 429 or error.code >= 500:
                    continue
                raise ClientError(f"Azure OpenAI returned {last} (not retried)") from None
            except (urllib.error.URLError, TimeoutError, OSError) as error:
                last = f"network error {type(error).__name__}"  # class name only: messages can echo the URL
                continue
            try:
                return self._parse(json.loads(raw))
            except (ValueError, TypeError, KeyError) as error:
                raise ClientError(f"unreadable Azure OpenAI reply ({type(error).__name__})") from None
        raise ClientError(f"Azure OpenAI failed after {self.retries + 1} attempts: {last}")

    def _parse(self, data: dict) -> Completion:
        usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
        self.reported_model = str(data.get("model") or "")
        if self.api == "chat":
            text = data["choices"][0]["message"]["content"] or ""
            return Completion(text.strip(), int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0))
        parts = [p.get("text") or "" for item in data.get("output") or [] if item.get("type") == "message"
                 for p in item.get("content") or [] if p.get("type") == "output_text"]
        return Completion("".join(parts).strip(), int(usage.get("input_tokens") or 0), int(usage.get("output_tokens") or 0))
