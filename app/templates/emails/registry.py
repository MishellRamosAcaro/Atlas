"""Email template registry and verification code template (registration flow)."""

from __future__ import annotations

from app.middleware.emails import EmailContext, EmailTemplateSpec

# ---------------------------------------------------------------------------
# Verification code (registration / confirm user)
# ---------------------------------------------------------------------------

VERIFICATION_CODE_FROM = "Fas-Agent <auth@email.fas-agent.com>"
VERIFICATION_CODE_SUBJECT_TEMPLATE = "Your verification code"

VERIFICATION_CODE_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta http-equiv="x-ua-compatible" content="ie=edge" />
  <title>Email verification</title>
</head>
<body style="margin:0; padding:0; background-color:#f4f6f8; font-family:Arial, Helvetica, sans-serif; color:#1f2937;">

  <div style="display:none; max-height:0; overflow:hidden; opacity:0; mso-hide:all;">
    Your Fas-Agent verification code is {code}
  </div>

  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%; margin:0; padding:24px 0; background-color:#f4f6f8;">
    <tr>
      <td align="center" style="padding:0 12px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:600px; background-color:#ffffff; border:1px solid #e5e7eb;">

          <tr>
            <td style="height:4px; line-height:4px; font-size:4px; background:#67e8f9;">&nbsp;</td>
          </tr>

          <tr>
            <td style="padding:20px 24px; text-align:center; background:#020617;">
              <div style="font-size:18px; line-height:24px; font-weight:700; color:#ffffff; letter-spacing:0.2px;">
                Field Application Specialist
              </div>
              <div style="font-size:12px; line-height:18px; margin-top:2px; color:#e2e8f0;">
                AI Agent
              </div>
            </td>
          </tr>

          <tr>
            <td style="padding:24px 24px 8px 24px;">
              <h1 style="margin:0; font-size:20px; line-height:28px; font-weight:700; color:#111827;">
                Verify your email
              </h1>
            </td>
          </tr>

          <tr>
            <td style="padding:0 24px 16px 24px; font-size:14px; line-height:22px; color:#4b5563;">
              Use the verification code below to confirm your identity.
            </td>
          </tr>

          <tr>
            <td style="padding:0 24px 24px 24px;">
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center" style="margin:0 auto; border-collapse:separate;">
                <tr>
                  <td align="center" style="padding:14px 24px; border:1px solid #d1d5db; background:#f8fafc; font-size:28px; line-height:32px; font-weight:700; letter-spacing:6px; color:#111827;">
                    {code}
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <tr>
            <td style="padding:0 24px 20px 24px; font-size:14px; line-height:22px; color:#4b5563;">
              If you did not request this code, you can safely ignore this email.
            </td>
          </tr>

          <tr>
            <td style="padding:16px 24px; background:#f8fafc; border-top:1px solid #e5e7eb; text-align:center; font-size:12px; line-height:18px; color:#6b7280;">
              This is an automated transactional email from Fas-Agent.
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>

</body>
</html>
"""


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


# Recipient (to) is taken from context["email"] via to_address_key.
VERIFICATION_CODE_SPEC = EmailTemplateSpec(
    from_address=VERIFICATION_CODE_FROM,
    to_address="",
    subject_template=VERIFICATION_CODE_SUBJECT_TEMPLATE,
    get_html=_verification_code_html,
    get_text=_verification_code_text,
    reply_to_key=None,
    to_address_key="email",
)

# Registration and template resolution live in app.middleware.emails (get_template_id).
# The service receives template_id ("contact" or "verification_code") and middleware returns the spec.
