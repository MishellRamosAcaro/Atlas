"""Contact form email template: spec, HTML variable, and body builders."""

from __future__ import annotations

from app.middleware.emails import EmailContext, EmailTemplateSpec

# HTML template for contact form email (placeholders filled in _contact_html)
CONTACT_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
</head>
<body style="margin:0; padding:0; background-color:#f4f6f8; font-family: Arial, Helvetica, sans-serif; color:#333;">

  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f6f8; padding:24px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff; border-radius:8px; overflow:hidden; box-shadow:0 4px 12px rgba(0,0,0,0.08);">
          <tr>
            <td style="padding:24px; text-align:center; background:#020617;">  
              <div style="font-size:13px; margin-top:6px; color:#a5f3fc;">
                Field Application Specialist
              </div>
              <div style="font-size:12px; color:#e2e8f0; margin-top:2px;">
                AI Agent
              </div>
            </td>
          </tr>

          <tr>
            <td style="padding:24px 24px 8px 24px;">
              <h2 style="margin:0; font-size:18px; color:#111;">New contact request</h2>
            </td>
          </tr>

          <tr>
            <td style="padding:8px 24px 24px 24px;">
              <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse; font-size:14px;">
                <tr>
                  <td style="padding:8px 12px 8px 0; font-weight:bold; width:120px;">Name</td>
                  <td style="padding:8px 0;">{name}</td>
                </tr>
                <tr>
                  <td style="padding:8px 12px 8px 0; font-weight:bold;">Email</td>
                  <td style="padding:8px 0;">{email}</td>
                </tr>
                <tr>
                  <td style="padding:8px 12px 8px 0; font-weight:bold;">Company</td>
                  <td style="padding:8px 0;">{company}</td>
                </tr>
                <tr>
                  <td style="padding:8px 12px 8px 0; font-weight:bold; vertical-align:top;">Message</td>
                  <td style="padding:8px 0; white-space:pre-wrap;">{message}</td>
                </tr>
              </table>
            </td>
          </tr>

          <tr>
            <td style="padding:16px 24px; background:#f1f5f9; text-align:center; font-size:12px; color:#64748b;">
              FAS-Agent · AI Agent Platform
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>

</body>
</html>
"""


def _escape_html(s: str) -> str:
    """Escape HTML special characters."""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _contact_html(context: EmailContext) -> str:
    """HTML body for contact form submission."""
    name = _escape_html(context.get("name", ""))
    email = _escape_html(context.get("email", ""))
    company = _escape_html(context.get("company", ""))
    message = _escape_html(context.get("message", ""))
    return CONTACT_HTML_TEMPLATE.format(
        name=name,
        email=email,
        company=company,
        message=message,
    )


def _contact_text(context: EmailContext) -> str:
    """Plain text body for contact form submission."""
    name = context.get("name", "")
    email = context.get("email", "")
    company = context.get("company", "")
    message = context.get("message", "")
    return f"""New contact request

Name: {name}
Email: {email}
Company: {company}

Message:
{message}
"""


CONTACT_SPEC = EmailTemplateSpec(
    from_address="contact@email.fas-agent.com",
    to_address="rnd@fas-agent.com",
    subject_template="New contact request from {name}",
    get_html=_contact_html,
    get_text=_contact_text,
    reply_to_key="email",
)
