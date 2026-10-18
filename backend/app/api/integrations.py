"""POST /api/integrations/shopify/webhooks — Shopify webhook receiver.

SIMULATED until a Shopify dev store exists: ``SHOPIFY_WEBHOOK_SECRET``
is unset, so the endpoint honestly returns 503 ("shopify_not_configured")
instead of pretending to process webhooks. When the secret IS
configured, the endpoint:

1. verifies ``X-Shopify-Hmac-Sha256`` against the raw body (401 on failure),
2. dedupes on ``X-Shopify-Webhook-Id`` (duplicate → 200, no reprocessing),
3. records the delivery in ``shopify_webhook_events`` + one ``audit_log`` row,
4. returns 200.

Even then it only RECORDS deliveries — no business action (no order
creation, no refunds) is taken automatically. Real processing against a
dev store is Phase 9b work (see docs/SHOPIFY.md).
"""

from __future__ import annotations

import json
import sqlite3

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from ..config import Settings
from ..integrations.webhooks import (
    record_tiktok_shop_webhook_event,
    record_webhook_event,
    verify_tiktok_shop_webhook,
    verify_webhook_hmac,
)
from ..security.audit import log_audit
from ..validators import body_within_cap
from .deps import get_db, get_settings

router = APIRouter()

_HMAC_HEADER = "X-Shopify-Hmac-Sha256"
_WEBHOOK_ID_HEADER = "X-Shopify-Webhook-Id"


@router.post("/integrations/shopify/webhooks")
async def shopify_webhook(
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    raw_body = await request.body()
    if not body_within_cap(raw_body, settings):
        return JSONResponse(
            status_code=413,
            content={"error": "payload_too_large"},
        )

    secret = settings.shopify_webhook_secret
    if not secret:
        # Honest 503: no dev store is connected; there is nothing real
        # to verify against. This is SIMULATED by design.
        return JSONResponse(
            status_code=503,
            content={
                "error": "shopify_not_configured",
                "detail": (
                    "Kein Shopify-Shop verbunden (Demo-Umgebung). "
                    "SHOPIFY_WEBHOOK_SECRET ist nicht gesetzt."
                ),
                "simulated": True,
            },
        )

    hmac_header = request.headers.get(_HMAC_HEADER)
    if not verify_webhook_hmac(raw_body, hmac_header, secret):
        log_audit(
            db,
            action="shopify_webhook_rejected",
            ip=request.client.host if request.client else None,
            details={"reason": "bad_hmac"},
        )
        db.commit()
        return JSONResponse(
            status_code=401,
            content={"error": "invalid_webhook_signature"},
        )

    webhook_id = request.headers.get(_WEBHOOK_ID_HEADER)
    if not webhook_id:
        return JSONResponse(
            status_code=400,
            content={"error": "missing_webhook_id"},
        )
    topic = request.headers.get("X-Shopify-Topic")
    shop_domain = request.headers.get("X-Shopify-Shop-Domain")

    is_new = record_webhook_event(db, webhook_id, topic, shop_domain)
    if not is_new:
        # Duplicate delivery: acknowledge, do NOT reprocess.
        db.commit()
        return {"status": "duplicate", "simulated": True}

    log_audit(
        db,
        action="shopify_webhook_received",
        ip=request.client.host if request.client else None,
        details={
            "webhook_id": webhook_id,
            "topic": topic,
            "shop_domain": shop_domain,
        },
    )
    db.commit()
    return {"status": "received", "simulated": True}



TT_KNOWN_WEBHOOK_TOPICS = frozenset({
    # TikTok Shop order lifecycle notifications (documented pattern).
    "ORDER_STATUS_CHANGE",
    "ORDER_CREATE",
})


def _tt_topic_detail(topic: str | None) -> dict:
    if topic not in TT_KNOWN_WEBHOOK_TOPICS:
        return {"unhandled": True}
    return {"handled": True}


@router.post("/integrations/tiktok-shop/webhooks")
async def tiktok_shop_webhook(
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """TikTok Shop webhook receiver: verify, dedupe, record, ack.

    Signature: HMAC-SHA256 hex of ``app_key + raw_body`` keyed with
    ``app_secret`` vs the ``authorization`` header (401 on failure).
    ``TIKTOK_SHOP_WEBHOOK_SECRET`` unset → honest 503
    (``tiktok_shop_not_configured``). Deliveries are only RECORDED —
    no business action is taken automatically.
    """
    raw_body = await request.body()
    if not body_within_cap(raw_body, settings):
        return JSONResponse(
            status_code=413,
            content={"error": "payload_too_large"},
        )
    secret = settings.tiktok_shop_webhook_secret
    app_key = settings.tiktok_shop_app_key
    if not secret or not app_key:
        return JSONResponse(
            status_code=503,
            content={
                "error": "tiktok_shop_not_configured",
                "detail": (
                    "Kein TikTok Shop verbunden (Demo-Umgebung). "
                    "TIKTOK_SHOP_WEBHOOK_SECRET ist nicht gesetzt."
                ),
            },
        )
    auth_header = request.headers.get("authorization")
    if not verify_tiktok_shop_webhook(raw_body, auth_header, app_key, secret):
        log_audit(
            db,
            action="tiktok_shop_webhook_rejected",
            ip=request.client.host if request.client else None,
            details={"reason": "bad_signature"},
        )
        db.commit()
        return JSONResponse(
            status_code=401,
            content={"error": "invalid_signature"},
        )
    try:
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        if not isinstance(payload, dict):
            payload = {}
    except (ValueError, UnicodeDecodeError):
        # Unparseable but signature-valid: acknowledge (avoid retry
        # storms), audit-note it, never crash.
        log_audit(
            db,
            action="tiktok_shop_webhook_received",
            ip=request.client.host if request.client else None,
            details={"unparseable": True},
        )
        db.commit()
        return {"status": "received", "received": True, "duplicate": False}
    notification_id = str(
        payload.get("tts_notification_id") or ""
    ).strip()
    if not notification_id:
        log_audit(
            db,
            action="tiktok_shop_webhook_rejected",
            ip=request.client.host if request.client else None,
            details={"reason": "missing_notification_id"},
        )
        db.commit()
        return JSONResponse(
            status_code=400,
            content={"error": "missing_notification_id"},
        )
    topic = payload.get("type") or payload.get("event")
    shop_id = payload.get("shop_id")
    is_new = record_tiktok_shop_webhook_event(
        db, notification_id, topic, shop_id
    )
    if not is_new:
        db.commit()
        return {"status": "duplicate", "received": True, "duplicate": True}
    detail = _tt_topic_detail(topic)
    log_audit(
        db,
        action="tiktok_shop_webhook_received",
        ip=request.client.host if request.client else None,
        details={
            "notification_id": notification_id,
            "topic": topic,
            "shop_id": shop_id,
            **detail,
        },
    )
    db.commit()
    return {"status": "received", "received": True, "duplicate": False}
