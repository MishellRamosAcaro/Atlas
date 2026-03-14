"""Contact form endpoint: POST /contact with rate limit, honeypot, BackgroundTasks."""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status

from app.limiter import limiter
from app.schemas.contact import ContactRequest, ContactResponse
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

router = APIRouter()


async def _send_contact_email_task(
    name: str, email: str, company: str, message: str
) -> None:
    """Background task: send contact email via Resend. Logs and swallows errors."""
    try:
        service = EmailService()
        await service.send_email(
            "contact",
            {"name": name, "email": email, "company": company, "message": message},
        )
    except httpx.HTTPStatusError as e:
        body = e.response.text
        try:
            body = e.response.json()
        except Exception:
            pass
        logger.exception(
            "Resend API error %s: %s. Response: %s",
            e.response.status_code,
            e.request.url,
            body,
        )
    except Exception as e:
        logger.exception("Failed to send contact email via Resend: %s", e)


@router.post(
    "",
    response_model=ContactResponse,
    summary="Submit contact form",
    description="Accepts contact form data, validates and checks honeypot; enqueues email send in background. Rate limited per IP. 400 if honeypot filled, 422 if validation fails, 429 if rate limit exceeded.",
)
@limiter.limit("5/minute")
async def submit_contact(
    request: Request,
    background_tasks: BackgroundTasks,
    body: ContactRequest,
) -> ContactResponse:
    """Submit contact form. Honeypot must be empty; otherwise 400. Email is sent in background."""
    if body.honeypot and body.honeypot.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request.",
        )
    background_tasks.add_task(
        _send_contact_email_task,
        body.name,
        body.email,
        body.company,
        body.message,
    )
    return ContactResponse()
