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
    record_webhook_event,
    record_woocommerce_webhook_event,
    verify_webhook_hmac,
    verify_woocommerce_webhook_signature,
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


def _safe_json_payload(raw_body: bytes) -> dict | None:
    """Parse a webhook body defensively: malformed JSON returns None
    instead of raising — the endpoint must never crash on it."""
    try:
        payload = json.loads(raw_body or b"{}")
    except (ValueError, TypeError):
        return None
    return payload if isinstance(payload, dict) else None


_WC_SIGNATURE_HEADER = "X-WC-Webhook-Signature"
_WC_DELIVERY_ID_HEADER = "X-WC-Webhook-Delivery-ID"

#: Webhook topics this endpoint understands. Anything else is recorded
#: as unhandled but still acknowledged with 200 (WooCommerce retries
#: non-2xx deliveries; retrying an unknown topic never helps).
WC_KNOWN_WEBHOOK_TOPICS = frozenset({"order.created", "order.updated"})


@router.post("/integrations/woocommerce/webhooks")
async def woocommerce_webhook(
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """WooCommerce webhook receiver.

    ``WOOCOMMERCE_WEBHOOK_SECRET`` unset → honest 503
    ("woocommerce_not_configured"). When configured:

    1. verifies ``X-WC-Webhook-Signature`` against the raw body (401),
    2. dedupes on ``X-WC-Webhook-Delivery-ID`` (duplicate → 200),
    3. parses the JSON payload defensively (malformed bodies never crash),
    4. handles ``order.created`` / ``order.updated`` (order number extracted
       for the audit log); unknown topics recorded as unhandled, still 200,
    5. records the delivery + one audit_log row, returns 200.

    Deliveries are only RECORDED — no business action is taken automatically.
    """
    raw_body = await request.body()
    if not body_within_cap(raw_body, settings):
        return JSONResponse(
            status_code=413,
            content={"error": "payload_too_large"},
        )

    secret = settings.woocommerce_webhook_secret
    if not secret:
        return JSONResponse(
            status_code=503,
            content={
                "error": "woocommerce_not_configured",
                "detail": (
                    "Kein WooCommerce-Shop verbunden (Demo-Umgebung). "
                    "WOOCOMMERCE_WEBHOOK_SECRET ist nicht gesetzt."
                ),
                "simulated": True,
            },
        )

    signature = request.headers.get(_WC_SIGNATURE_HEADER)
    if not verify_woocommerce_webhook_signature(raw_body, signature, secret):
        log_audit(
            db,
            action="woocommerce_webhook_rejected",
            ip=request.client.host if request.client else None,
            details={"reason": "bad_signature"},
        )
        db.commit()
        return JSONResponse(
            status_code=401,
            content={"error": "invalid_webhook_signature"},
        )

    delivery_id = request.headers.get(_WC_DELIVERY_ID_HEADER)
    if not delivery_id:
        return JSONResponse(
            status_code=400,
            content={"error": "missing_delivery_id"},
        )
    topic = request.headers.get("X-WC-Webhook-Topic")

    is_new = record_woocommerce_webhook_event(db, delivery_id, topic)
    if not is_new:
        # Duplicate delivery: acknowledge, do NOT reprocess.
        db.commit()
        return {"status": "duplicate", "simulated": True}

    payload = _safe_json_payload(raw_body)
    topic_info = _wc_topic_detail(topic, payload)
    log_audit(
        db,
        action="woocommerce_webhook_received",
        ip=request.client.host if request.client else None,
        details={
            "delivery_id": delivery_id,
            "topic": topic,
            **topic_info,
        },
    )
    db.commit()
    return {"status": "received", "simulated": True}


def _wc_topic_detail(topic: str | None, payload: dict | None) -> dict:
    """Extract audit-friendly detail for a WooCommerce webhook topic.

    Known topics yield the merchant-facing order reference when the
    payload carries one; unknown topics (or unparseable payloads) are
    marked as unhandled — recorded, never processed, never fatal.
    """
    if payload is None:
        return {"handled": False, "note": "unparseable_payload"}
    if topic not in WC_KNOWN_WEBHOOK_TOPICS:
        return {"handled": False, "note": "unhandled_topic"}
    order_ref = payload.get("number") or payload.get("order_number")
    if order_ref is None:
        order_id = payload.get("id")
        order_ref = f"id:{order_id}" if order_id is not None else None
    return {"handled": True, "order_ref": order_ref}
