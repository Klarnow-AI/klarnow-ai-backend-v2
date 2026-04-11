"""Email notifications for pipeline events.

Uses Resend (already configured in the codebase) to send transactional
emails when key pipeline events occur.
"""
from __future__ import annotations

from uuid import UUID

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("klarnow.notifications.email")

PIPELINE_COMPLETE_SUBJECT = "Your brand package is ready"


def _build_pipeline_complete_html(
    brand_name: str,
    results_url: str,
    logo_url: str | None = None,
) -> str:
    """Build HTML email for pipeline completion."""
    logo_block = ""
    if logo_url:
        logo_block = f"""
        <div style="text-align: center; margin: 24px 0;">
            <img src="{logo_url}" alt="{brand_name} logo"
                 style="max-height: 80px; max-width: 200px;" />
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f9fafb;">
        <div style="max-width: 560px; margin: 0 auto; padding: 40px 20px;">
            <div style="background: white; border-radius: 16px; padding: 40px 32px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);">
                {logo_block}

                <h1 style="font-size: 24px; font-weight: 700; color: #111827; margin: 0 0 8px 0; text-align: center;">
                    Your brand package is ready
                </h1>

                <p style="font-size: 15px; color: #6b7280; line-height: 1.6; text-align: center; margin: 0 0 28px 0;">
                    All 12 agents have finished building the complete brand package
                    for <strong style="color: #111827;">{brand_name}</strong>.
                    Your strategy, identity, logo, website, creative assets,
                    and social graphics are ready to download.
                </p>

                <div style="text-align: center; margin: 0 0 28px 0;">
                    <a href="{results_url}"
                       style="display: inline-block; padding: 14px 32px; background: #111827; color: white; text-decoration: none; border-radius: 10px; font-size: 15px; font-weight: 600;">
                        View Brand Package
                    </a>
                </div>

                <div style="border-top: 1px solid #f3f4f6; padding-top: 20px; margin-top: 8px;">
                    <p style="font-size: 13px; color: #9ca3af; text-align: center; margin: 0;">
                        You can also download all assets as a ZIP from the results page.
                    </p>
                </div>
            </div>

            <p style="font-size: 12px; color: #9ca3af; text-align: center; margin-top: 24px;">
                Sent by GrowthAgent. You received this because your brand pipeline completed.
            </p>
        </div>
    </body>
    </html>
    """


def _build_pipeline_complete_text(brand_name: str, results_url: str) -> str:
    """Build plain text email for pipeline completion."""
    return (
        f"Your brand package for {brand_name} is ready.\n\n"
        f"All 12 agents have finished building your complete brand package "
        f"including strategy, identity, logo, website, creative assets, and social graphics.\n\n"
        f"View your brand package: {results_url}\n\n"
        f"You can also download all assets as a ZIP from the results page.\n\n"
        f"-- GrowthAgent"
    )


def send_pipeline_complete_email(
    *,
    to_email: str,
    brand_name: str,
    pack_id: str | UUID,
    logo_url: str | None = None,
    base_url: str | None = None,
) -> bool:
    """Send email notification when the full pipeline completes.

    Args:
        to_email: Recipient email address
        brand_name: The brand name for the subject line
        pack_id: Pack ID for constructing the results URL
        logo_url: Optional logo URL for the email header
        base_url: Frontend base URL (falls back to settings)

    Returns:
        True if email sent successfully, False otherwise
    """
    settings = get_settings()

    if not settings.resend_api_key:
        logger.info("Pipeline completion email skipped: Resend not configured")
        return False

    if not to_email:
        logger.info("Pipeline completion email skipped: no recipient")
        return False

    frontend_base = base_url or getattr(settings, "frontend_url", "") or "https://app.growthagent.co"
    results_url = f"{frontend_base}/packs/{pack_id}/results"

    try:
        import resend
        resend.api_key = settings.resend_api_key

        from_email = settings.resend_from_email or "noreply@growthagent.co"
        html = _build_pipeline_complete_html(brand_name, results_url, logo_url)
        text = _build_pipeline_complete_text(brand_name, results_url)

        resend.Emails.send({
            "from": from_email,
            "to": to_email,
            "subject": f"{PIPELINE_COMPLETE_SUBJECT} - {brand_name}",
            "html": html,
            "text": text,
        })

        logger.info(
            "Pipeline completion email sent to=%s brand=%s pack=%s",
            to_email, brand_name, pack_id,
        )
        return True

    except Exception as e:
        logger.error(
            "Failed to send pipeline completion email to=%s error=%s",
            to_email, e,
        )
        return False
