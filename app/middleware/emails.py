"""Email middleware: template spec type and registry to choose template by id."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

# Type for context passed to get_html / get_text
EmailContext = dict[str, str]


@dataclass(frozen=True)
class EmailTemplateSpec:
    """Specification for an email template: addresses, subject, body builders, reply_to."""

    from_address: str
    to_address: str
    subject_template: str
    get_html: Callable[[EmailContext], str]
    get_text: Callable[[EmailContext], str]
    reply_to_key: str | None = None  # Key in context for Reply-To (e.g. "email")
    to_address_key: str | None = None  # Key in context for dynamic "to" (e.g. "email")


# _EMAIL_TEMPLATE: template_id -> spec (contact vs verification_code)
_EMAIL_TEMPLATE: dict[str, EmailTemplateSpec] = {}


def add_email_template(template_id: str, spec: EmailTemplateSpec) -> None:
    """Add an email template to the registry. Called at startup with contact and verification specs."""
    _EMAIL_TEMPLATE[template_id] = spec


def get_template_id(template_id: str) -> EmailTemplateSpec:
    """Return the spec for the given template id. Raises KeyError if unknown."""
    if template_id not in _EMAIL_TEMPLATE:
        raise KeyError(f"Unknown email template: {template_id!r}")
    return _EMAIL_TEMPLATE[template_id]


# Register built-in templates (contact form and verification code)
from app.templates.emails.contact import CONTACT_SPEC  # noqa: E402
from app.templates.emails.registry import VERIFICATION_CODE_SPEC  # noqa: E402

add_email_template("contact", CONTACT_SPEC)
add_email_template("verification_code", VERIFICATION_CODE_SPEC)
