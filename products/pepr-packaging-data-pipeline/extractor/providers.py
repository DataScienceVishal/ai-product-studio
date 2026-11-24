"""Model providers. Interface: complete(system, parts, max_output_tokens) -> Completion.
parts: [{"type":"text","text":..} | {"type":"image","media_type":..,"data_b64":..}].
FakeProvider: deterministic, no network. AzureResponsesProvider: Azure OpenAI v1 Responses API; refuses to run unless
T56_SPEND_APPROVED=1 (Vishal's spend approval, Q-11). Keys come from the environment only and are never logged."""
import json
import os
import re
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from . import vocab

IMAGE_TOKENS_WORST = 6000  # conservative upper bound per page image (high detail, tiled)
REASONING_EFFORTS = ("low", "medium", "high")


@dataclass(frozen=True)
class Completion:
    text: str
    input_tokens: int
    output_tokens: int  # includes reasoning tokens
    model: str


class ProviderError(RuntimeError):
    """Call failed. billed_* are tokens that may have been billed anyway; `may_have_run` means charge the worst case."""

    def __init__(self, message, input_tokens=0, output_tokens=0, may_have_run=False, fatal=False):
        super().__init__(message)
        self.fatal = fatal  # rejected request or credentials: every sheet would fail the same way, stop the run
        self.input_tokens, self.output_tokens, self.may_have_run = input_tokens, output_tokens, may_have_run


class SpendNotApproved(RuntimeError):
    pass


def estimate_input_tokens(system, parts):
    """Upper bound: one token per UTF-8 byte of text, plus a fixed worst case per image."""
    n = len(system.encode("utf-8"))
    for p in parts:
        n += len(p["text"].encode("utf-8")) if p["type"] == "text" else IMAGE_TOKENS_WORST
    return n


class FakeProvider:
    """Deterministic and offline. Without `responder` it finds component names in the text and returns every plausible
    feature key as missing (valid shape, no values). `responder(system, parts) -> str` lets tests script the answer."""
    name = "fake"
    output_headroom = 0

    def __init__(self, responder=None):
        self.responder = responder
        self.calls = []

    def complete(self, system, parts, max_output_tokens):
        self.calls.append(parts)
        if self.responder:
            text = self.responder(system, parts)
        else:
            blob = " ".join(p["text"] for p in parts if p["type"] == "text").lower()
            comps, seen = [], set()
            for m in re.finditer(r"[a-z]+(?: [a-z]+)?", blob):
                n = vocab.tx.norm_name(m.group(0))
                if n in vocab.PLAUSIBLE and n not in seen:
                    seen.add(n)
                    comps.append({"name": n, "material": {"status": "missing"}, "colour": {"status": "missing"},
                                  "weight_g": {"status": "missing"},
                                  "features": {k: {"status": "missing"} for k in vocab.PLAUSIBLE[n]}})
            text = json.dumps({"components": comps})
        return Completion(text, estimate_input_tokens(system, parts) // 4, max(len(text) // 4, 1), "fake")


def _image_url(p):
    return f"data:{p['media_type']};base64,{p['data_b64']}"


def default_transport(req, timeout):
    """-> (status, headers dict, body bytes). Raises socket.timeout / URLError on transport problems."""
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read()


class AzureResponsesProvider:
    name = "azure"

    def __init__(self, endpoint=None, deployment=None, api_key=None, reasoning_effort=None, timeout=300.0, retries=3,
                 backoff=2.0, transport=default_transport, sleep=time.sleep, env=None):
        env = os.environ if env is None else env
        if env.get("T56_SPEND_APPROVED") != "1":
            raise SpendNotApproved("Azure provider refused: set T56_SPEND_APPROVED=1 once Vishal has approved spend (Q-11)")
        endpoint = endpoint or env.get("AZURE_OPENAI_ENDPOINT", "")
        if not endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT is not set")
        effort = reasoning_effort or env.get("T56_REASONING_EFFORT", "low")
        if effort not in REASONING_EFFORTS:
            raise ValueError(f"reasoning effort must be one of {REASONING_EFFORTS}")
        root = endpoint.strip().rstrip("/")
        for suffix in ("/openai/v1/responses", "/openai/v1", "/openai"):
            if root.lower().endswith(suffix):
                root = root[: -len(suffix)]
        self.url = root.rstrip("/") + "/openai/v1/responses"
        self.deployment = deployment or env.get("T56_DEPLOYMENT", "gpt-5.4-pro")
        self._key = api_key or env.get("AZURE_OPENAI_API_KEY", "") or "proxy-injected"
        self.reasoning_effort = effort
        self.output_headroom = 0  # max_output_tokens already covers reasoning; the guard reserves all of it
        self.timeout, self.retries, self.backoff = timeout, retries, backoff
        self.transport, self.sleep, self._env = transport, sleep, env

    def payload(self, system, parts, max_output_tokens):
        content = []
        for p in parts:
            if p["type"] == "text":
                content.append({"type": "input_text", "text": p["text"]})
            else:
                content.append({"type": "input_image", "image_url": _image_url(p), "detail": "high"})
        return {"model": self.deployment, "instructions": system, "max_output_tokens": int(max_output_tokens),
                "reasoning": {"effort": self.reasoning_effort}, "store": False,
                "input": [{"role": "user", "content": content}]}

    def complete(self, system, parts, max_output_tokens):
        if self._env.get("T56_SPEND_APPROVED") != "1":  # checked again at call time
            raise SpendNotApproved("Azure call refused: T56_SPEND_APPROVED is not 1")
        body = json.dumps(self.payload(system, parts, max_output_tokens)).encode()
        worst_in = estimate_input_tokens(system, parts)
        last = "no attempt made"
        for attempt in range(self.retries + 1):
            req = urllib.request.Request(self.url, data=body, method="POST",
                                         headers={"api-key": self._key, "Content-Type": "application/json"})
            try:
                status, headers, raw = self.transport(req, self.timeout)
            except (socket.timeout, TimeoutError) as e:  # sent, then no answer: it may have run; never resend
                raise ProviderError(f"timeout after {self.timeout}s ({type(e).__name__})", worst_in,
                                    max_output_tokens, may_have_run=True) from None
            except urllib.error.URLError as e:
                if isinstance(getattr(e, "reason", None), (socket.timeout, TimeoutError)):
                    raise ProviderError("timeout", worst_in, max_output_tokens, may_have_run=True) from None
                last = f"connection error ({type(e.reason).__name__})"  # never reached the model: no cost, retry
                self._pause(attempt, None)
                continue
            if status == 429 or status >= 500:
                last = f"HTTP {status}"
                self._pause(attempt, headers.get("retry-after") or headers.get("Retry-After"))
                continue
            if status in (401, 403):
                raise ProviderError(f"credentials rejected (HTTP {status})", fatal=True)
            if status >= 400:
                raise ProviderError(f"request rejected (HTTP {status}): {raw[:300].decode('utf-8', 'replace')}", fatal=True)
            return self._parse(raw, worst_in, max_output_tokens)
        raise ProviderError(f"gave up after {self.retries + 1} attempts: {last}")

    def _pause(self, attempt, retry_after):
        if attempt >= self.retries:
            return
        try:
            wait = min(float(retry_after), 60.0) if retry_after else self.backoff * (2 ** attempt)
        except ValueError:
            wait = self.backoff * (2 ** attempt)
        self.sleep(wait)

    def _parse(self, raw, worst_in, max_out):
        try:
            data = json.loads(raw)
            usage = data.get("usage") or {}
            used_in, used_out = int(usage.get("input_tokens") or 0), int(usage.get("output_tokens") or 0)
            text = "".join(part.get("text", "") for item in data.get("output", []) if item.get("type") == "message"
                           for part in item.get("content", []) if part.get("type") == "output_text").strip()
            status = data.get("status")
        except (ValueError, AttributeError, TypeError):
            raise ProviderError("unreadable response", worst_in, max_out, may_have_run=True) from None
        if status not in (None, "completed") or not text:
            raise ProviderError(f"no usable answer (status {status!r})", used_in, used_out)
        return Completion(text, used_in, used_out, data.get("model", self.deployment))
