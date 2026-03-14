"""Email sending service using Resend Python SDK."""

from __future__ import annotations

import asyncio
from typing import Any

import resend

from app.config import get_settings
from app.middleware.emails import get_template_id


class EmailService:
    """Service for sending emails via Resend SDK."""

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.resend_api_key

    def _send_resend(self, params: dict[str, Any]) -> dict[str, Any]:
        """Send email via Resend SDK (sync). Sets api_key and calls Emails.send."""
        if not self._api_key:
            raise ValueError("RESEND_API_KEY is not configured.")
        resend.api_key = self._api_key
        return resend.Emails.send(params)

    async def send_email(
        self, template_id: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Send an email using a registered template.
        Resolves from/to, subject, html, text and optional reply_to from the template spec.
        """
        spec = get_template_id(template_id)
        str_context = {k: str(v) for k, v in context.items()}
        subject = spec.subject_template.format(**str_context)
        html = spec.get_html(str_context)
        text = spec.get_text(str_context)

        to_addr = spec.to_address
        if getattr(spec, "to_address_key", None) and spec.to_address_key in context:
            to_addr = str(context[spec.to_address_key])
        to_list = [to_addr] if to_addr else []

        params: dict[str, Any] = {
            "from": spec.from_address,
            "to": to_list,
            "subject": subject,
            "html": html,
            "text": text,
        }
        if spec.reply_to_key and spec.reply_to_key in context:
            params["reply_to"] = str(context[spec.reply_to_key])

        return await asyncio.to_thread(self._send_resend, params)
