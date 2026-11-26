"""map_names(rows, client): batch names, validate the reply strictly, never repair it.

A reply that is malformed, or leaves an id out, repeats an id or uses a category outside the nine, makes those rows
"UNMAPPED". They count as wrong in scoring. There are no retries with a changed prompt (kill-test rule). The only
retry is the transport's: same request again after a network error, 429 or 5xx.
"""
from __future__ import annotations

import http.client
import json
import math
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

if __package__ in (None, ""):
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mapper.prompt import (CATEGORIES, REASONING_EFFORT, RESPONSE_SCHEMA, SCHEMA_NAME, SYSTEM_PROMPT,
                           build_user_message)

UNMAPPED = "UNMAPPED"
_LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")
DEFAULT_BATCH_SIZE = 200
MAX_OUTPUT_TOKENS = 16000  # reasoning tokens count inside this on gpt-5-mini; 200 answers need only ~4,000


def estimate_input_tokens(system: str, user: str) -> int:
    """Deliberately high estimate (3 characters per token, English averages about 4) for the pre-send spend cap."""
    return math.ceil((len(system) + len(user)) / 3)


def worst_case_usd(input_tokens: int, max_output_tokens: int, price: tuple[float, float]) -> float:
    """Dollars if the request used every token it may: the whole estimated input plus the full output cap."""
    return (input_tokens * price[0] + max_output_tokens * price[1]) / 1_000_000


def check_price(price) -> tuple[float, float]:
    """The price config must be two finite numbers above zero, or no spend can be bounded."""
    try:
        pin, pout = float(price[0]), float(price[1])
    except (TypeError, ValueError, IndexError, KeyError):
        raise ValueError("price config is missing or unreadable: no spend cap can be computed") from None
    if not (math.isfinite(pin) and math.isfinite(pout)) or pin <= 0 or pout <= 0:
        raise ValueError("price config must be above zero for input and output: no spend cap can be computed")
    return pin, pout


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never follow a redirect: it would carry the api-key header to another host. A 3xx surfaces as HTTPError."""

    def redirect_request(self, *args, **kwargs):
        return None


_NO_REDIRECT_OPENER = urllib.request.build_opener(_NoRedirect)


class ClientError(Exception):
    """A transport or API failure with a message that never contains a key. Carries any usage the API reported."""

    def __init__(self, message: str, http_code: int | None = None, input_tokens: int = 0, output_tokens: int = 0,
                 attempts: int = 0):
        super().__init__(message)
        self.http_code, self.input_tokens, self.output_tokens, self.attempts = http_code, input_tokens, output_tokens, attempts


@dataclass
class Completion:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    finish_reason: str = ""
    attempts: int = 1


@dataclass
class MapResult:
    predictions: dict[str, str]
    input_tokens: int = 0
    output_tokens: int = 0
    requests: int = 0
    replies: int = 0  # replies received (even if invalid): once > 0 the one shot is used
    errors: list[str] = field(default_factory=list)
    failures: list[dict] = field(default_factory=list)  # batches that got no answer
    finish_reasons: list[str] = field(default_factory=list)
    transport_attempts: list[int] = field(default_factory=list)

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
    if not isinstance(data, dict) or not isinstance(data.get("mappings"), list):
        return result, ['reply is not an object with a "mappings" array']
    data = data["mappings"]
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


def map_names(rows: list[dict], client, batch_size: int = DEFAULT_BATCH_SIZE, into: MapResult | None = None) -> MapResult:
    """`into`: a result to fill in place, so a caller keeps what was counted if this raises."""
    ids = [r["id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("input ids are not unique")
    out = into if into is not None else MapResult(predictions={})
    for start in range(0, len(rows), batch_size):
        batch = rows[start:start + batch_size]
        batch_ids = [r["id"] for r in batch]
        out.requests += 1
        try:
            completion = client.complete(SYSTEM_PROMPT, build_user_message(batch))
        except Exception as error:  # no answer: a ClientError, or anything unexpected before a reply was parsed
            failure = {"batch": out.requests, "error_class": type(error).__name__,
                       "http_code": getattr(error, "http_code", None),
                       "message": str(error)[:300] if isinstance(error, ClientError) else "",
                       "input_tokens": getattr(error, "input_tokens", 0), "output_tokens": getattr(error, "output_tokens", 0),
                       "transport_attempts": getattr(error, "attempts", 0)}
            out.failures.append(failure)
            out.input_tokens += failure["input_tokens"]
            out.output_tokens += failure["output_tokens"]
            out.errors.append(f"batch {out.requests}: no answer ({failure['error_class']})")
            out.predictions.update({i: UNMAPPED for i in batch_ids})
            continue
        out.replies += 1
        out.input_tokens += completion.input_tokens
        out.output_tokens += completion.output_tokens
        out.finish_reasons.append(completion.finish_reason)
        out.transport_attempts.append(completion.attempts)
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
        text = json.dumps({"mappings": answer})
        return Completion(text, len(system) // 4 + len(user) // 4, len(text) // 4, "stop")

    def settings(self) -> dict:
        return {"api": "fake"}


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
    No temperature (gpt-5-mini rejects it). Strict structured output (JSON schema, category enum) and reasoning effort
    "low" are sent on both APIs. The key goes only in the api-key header and is never logged.
    """
    name = "azure"

    def __init__(self, endpoint: str, deployment: str = "gpt-5-mini", api_key: str = "", api: str = "auto",
                 timeout: float = 180.0, retries: int = 2, sleep=time.sleep, opener=None,
                 max_output_tokens: int = MAX_OUTPUT_TOKENS, reasoning_effort: str = REASONING_EFFORT,
                 allow_insecure_localhost: bool = False):
        if not endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT is not set")
        parts = urllib.parse.urlsplit(endpoint.strip())
        local_ok = allow_insecure_localhost and parts.scheme == "http" and (parts.hostname or "") in _LOCAL_HOSTS
        if parts.scheme != "https" and not local_ok:
            raise ValueError("AZURE_OPENAI_ENDPOINT must start with https:// (the api-key is sent in a header)")
        if not parts.hostname:
            raise ValueError("AZURE_OPENAI_ENDPOINT has no host name")
        if api == "auto":
            api = "responses" if endpoint.strip().rstrip("/").lower().endswith("/openai/v1/responses") else "chat"
        if api not in ("chat", "responses"):
            raise ValueError("AZURE_OPENAI_API must be auto, chat or responses")
        self.api, self.deployment = api, deployment
        self.url = _normalise_endpoint(endpoint) + (
            "/openai/v1/responses" if api == "responses" else "/openai/v1/chat/completions")
        self._key = api_key
        self._headers = {"api-key": api_key or "proxy-injected", "Content-Type": "application/json"}
        self.timeout, self.retries, self.sleep = timeout, retries, sleep
        self.opener = opener or _NO_REDIRECT_OPENER.open
        self.spend_cap_usd: float | None = None
        self.price: tuple[float, float] | None = None
        self.committed_usd = 0.0  # worst case of every attempt sent so far, retries included
        self.max_output_tokens, self.reasoning_effort = max_output_tokens, reasoning_effort
        self.reported_model = ""

    @classmethod
    def from_env(cls, env=None, allow_insecure_localhost: bool = False) -> "AzureOpenAIClient":
        env = os.environ if env is None else env
        return cls(env.get("AZURE_OPENAI_ENDPOINT", ""), env.get("AZURE_OPENAI_DEPLOYMENT") or "gpt-5-mini",
                   env.get("AZURE_OPENAI_API_KEY", ""), env.get("AZURE_OPENAI_API") or "auto",
                   allow_insecure_localhost=allow_insecure_localhost)

    def set_spend_cap(self, cap_usd: float, price: tuple[float, float]) -> None:
        self.price = check_price(price)
        if not (math.isfinite(cap_usd) and cap_usd > 0):
            raise ValueError("spend cap must be above zero")
        self.spend_cap_usd = float(cap_usd)

    def settings(self) -> dict:
        return {"api": self.api, "max_output_tokens": self.max_output_tokens, "reasoning_effort": self.reasoning_effort,
                "structured_output": "json_schema strict", "timeout_s": self.timeout, "transport_retries": self.retries}

    def _payload(self, system: str, user: str) -> dict:
        schema = {"name": SCHEMA_NAME, "strict": True, "schema": RESPONSE_SCHEMA}
        if self.api == "responses":
            return {"model": self.deployment, "instructions": system, "max_output_tokens": self.max_output_tokens,
                    "store": False, "input": [{"role": "user", "content": user}],
                    "reasoning": {"effort": self.reasoning_effort},
                    "text": {"format": {"type": "json_schema", **schema}}}
        return {"model": self.deployment, "max_completion_tokens": self.max_output_tokens,
                "reasoning_effort": self.reasoning_effort,
                "response_format": {"type": "json_schema", "json_schema": schema},
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}

    def _redact(self, text: str) -> str:
        return text.replace(self._key, "[redacted]") if self._key else text

    def _http_detail(self, error: urllib.error.HTTPError) -> str:
        """Azure's error code and a short message, key redacted. Never the headers."""
        try:
            err = json.loads(error.read()).get("error", {})
            code, message = str(err.get("code") or ""), str(err.get("message") or "")
        except Exception:  # unreadable body: the status code alone is reported
            return ""
        return self._redact(f" [{code}] {message}"[:300])

    def complete(self, system: str, user: str) -> Completion:
        body = json.dumps(self._payload(system, user)).encode("utf-8")
        last, code = "unknown error", None
        worst = 0.0
        if self.spend_cap_usd is not None:
            worst = worst_case_usd(estimate_input_tokens(system, user), self.max_output_tokens, self.price)
        for attempt in range(self.retries + 1):
            if self.spend_cap_usd is not None:  # every attempt, a retry too, may be billed in full
                if self.committed_usd + worst > self.spend_cap_usd + 1e-9:
                    raise ClientError(f"spend cap ${self.spend_cap_usd:.2f} would be exceeded: request not sent",
                                      attempts=attempt)
                self.committed_usd += worst
            if attempt:
                self.sleep(min(2 ** attempt, 20))  # same request again: backoff 2s, 4s
            request = urllib.request.Request(self.url, data=body, headers=self._headers, method="POST")
            try:
                with self.opener(request, timeout=self.timeout) as response:
                    raw = response.read()
            except urllib.error.HTTPError as error:
                code, last = error.code, f"HTTP {error.code}"
                if error.code == 429 or error.code >= 500:
                    continue
                raise ClientError(f"Azure OpenAI returned {last}{self._http_detail(error)} (not retried)",
                                  http_code=error.code, attempts=attempt + 1) from None
            except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException) as error:
                code, last = None, f"network error {type(error).__name__}"  # class name only: messages can echo the URL
                continue
            try:
                data = json.loads(raw)
            except (ValueError, TypeError):
                raise ClientError("unreadable Azure OpenAI reply (not JSON)", attempts=attempt + 1) from None
            if not isinstance(data, dict):
                raise ClientError("unreadable Azure OpenAI reply (not an object)", attempts=attempt + 1)
            return self._parse(data, attempt + 1)
        raise ClientError(f"Azure OpenAI failed after {self.retries + 1} attempts: {last}", http_code=code,
                          attempts=self.retries + 1)

    @staticmethod
    def _count(value) -> int:
        try:
            return max(int(value or 0), 0)
        except (TypeError, ValueError):
            return 0

    def _parse(self, data: dict, attempts: int) -> Completion:
        """A reply arrived, so usage is kept whatever its shape: a wrong shape gives empty text (all UNMAPPED)."""
        usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
        self.reported_model = str(data.get("model") or "")
        text, reason = "", ""
        try:
            if self.api == "chat":
                inp, out = self._count(usage.get("prompt_tokens")), self._count(usage.get("completion_tokens"))
                choice = data["choices"][0]
                reason = str(choice.get("finish_reason") or "")
                content = choice["message"]["content"]
                text = content.strip() if isinstance(content, str) else ""
            else:
                inp, out = self._count(usage.get("input_tokens")), self._count(usage.get("output_tokens"))
                reason = str(data.get("status") or "")
                if reason == "incomplete" and isinstance(data.get("incomplete_details"), dict):
                    reason += ":" + str(data["incomplete_details"].get("reason") or "")
                text = "".join(p.get("text") or "" for item in data.get("output") or [] if item.get("type") == "message"
                               for p in item.get("content") or [] if p.get("type") == "output_text").strip()
        except (KeyError, IndexError, TypeError, AttributeError, ValueError):
            reason = reason or "unreadable_shape"
            text = ""
            inp = self._count(usage.get("prompt_tokens") or usage.get("input_tokens"))
            out = self._count(usage.get("completion_tokens") or usage.get("output_tokens"))
        return Completion(text, inp, out, reason, attempts)
