import logging

import httpx

from icu.config import settings

log = logging.getLogger("icu.email")


async def send_otp_email(to_email: str, code: str) -> bool:
    """Send OTP via Resend HTTP API when ICU_RESEND_API_KEY is set; otherwise log only."""
    if settings.resend_api_key and settings.resend_from_email:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {settings.resend_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "from": settings.resend_from_email,
                        "to": [to_email],
                        "subject": "Your ICU login code",
                        "text": f"Your verification code is: {code}\n\nIt expires in a few minutes.",
                    },
                )
            if r.status_code >= 400:
                log.error("Resend error %s: %s", r.status_code, r.text)
                return False
            return True
        except Exception as e:
            log.exception("Resend send failed: %s", e)
            return False
    log.info("OTP email (no provider configured): to=%s code=%s", to_email, code)
    return True
