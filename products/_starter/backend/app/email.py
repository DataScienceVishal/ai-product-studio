"""Email adapter. Sending real email is a paid service, so it needs approval (playbooks/safety.md).

OutboxEmail keeps messages in memory for dev and tests and logs only that a message was sent.
It never logs the address or the body, because reset links carry secrets.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Protocol

log = logging.getLogger("app.email")


@dataclass
class Message:
    to: str
    subject: str
    body: str


class EmailSender(Protocol):
    def send(self, to: str, subject: str, body: str) -> None: ...


@dataclass
class OutboxEmail:
    sent: list[Message] = field(default_factory=list)
    limit: int = 200  # bound memory in long-running dev servers

    def send(self, to: str, subject: str, body: str) -> None:
        self.sent.append(Message(to, subject, body))
        del self.sent[:-self.limit]
        log.info("email queued", extra={"subject": subject})
