"""Email template registry and verification code template (registration flow)."""

from __future__ import annotations

from app.middleware.emails import EmailContext, EmailTemplateSpec
# ---------------------------------------------------------------------------
# Verification code (registration / confirm user)
# ---------------------------------------------------------------------------

VERIFICATION_CODE_FROM = "FastAgent <noreply@contact.fastagent.com>"
VERIFICATION_CODE_SUBJECT_TEMPLATE = "Your verification code: {code}"

# HTML template for verification code email
VERIFICATION_CODE_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: sans-serif; line-height: 1.5; color: #333;">
  <h2 style="color: #111;">Verify your email</h2>
  <p>Use this code to confirm your identity:</p>
  <p style="font-size: 1.25rem; font-weight: bold; letter-spacing: 0.1em;">{code}</p>
  <p>If you did not request this, you can ignore this email.</p>
</body>
</html>"""


def _verification_code_html(context: EmailContext) -> str:
    """HTML body for verification code email."""
    code = context.get("code", "")
    return VERIFICATION_CODE_HTML_TEMPLATE.format(code=code)


def _verification_code_text(context: EmailContext) -> str:
    """Plain text body for verification code email."""
    code = context.get("code", "")
    return f"""Verify your email

Use this code to confirm your identity: {code}

If you did not request this, you can ignore this email.
"""


# Recipient (to) is the user's email from context["email"]; when the service supports
# dynamic "to" (e.g. to_address_key), register this spec and use it.
VERIFICATION_CODE_SPEC = EmailTemplateSpec(
    from_address=VERIFICATION_CODE_FROM,
    to_address="",  # At send time, use context["email"]; service must support to_address_key (TODO)
    subject_template=VERIFICATION_CODE_SUBJECT_TEMPLATE,
    get_html=_verification_code_html,
    get_text=_verification_code_text,
    reply_to_key=None,
)

# Registration and template resolution live in app.middleware.emails (get_template_id).
# The service receives template_id ("contact" or "verification_code") and middleware returns the spec.
