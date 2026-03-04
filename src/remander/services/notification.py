"""Notification sender protocol — pluggable interface for sending notifications."""

from typing import Protocol, runtime_checkable


# Reason: protocol class — attrs not needed for abstract interface definition
@runtime_checkable
class NotificationSender(Protocol):
    async def send(
        self,
        subject: str,
        body: str,
        *,
        html_body: str | None = None,
    ) -> None: ...
