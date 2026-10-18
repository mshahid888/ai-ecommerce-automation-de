"""Store integrations (Phase 9): interface, adapters, factory.

``get_store_integration()`` is the single place that decides which
``StoreIntegration`` the pipeline uses. ``STORE_BACKEND`` (env):
``demo`` (default) → ``DemoStoreAdapter``;
``shopify_simulated`` → ``SimulatedShopifyAdapter``. Unknown values
fall back to ``demo``.

``ShopifyAdapter`` (real Admin API skeleton) is NOT selectable here —
it is constructed explicitly, in code, only when a dev store exists.
"""

from __future__ import annotations

import logging
import sqlite3
from typing import TYPE_CHECKING

from .base import (
    IntegrationConfigError,
    IntegrationError,
    StoreIntegration,
)
from .demo import DemoStoreAdapter
from .shopify import ShopifyAdapter
from .shopify_simulated import SimulatedShopifyAdapter
from .tiktok_shop import TikTokShopAdapter
from .webhooks import (
    record_tiktok_shop_webhook_event,
    record_webhook_event,
    verify_tiktok_shop_webhook,
    verify_webhook_hmac,
)

if TYPE_CHECKING:  # pragma: no cover
    from ..config import Settings

__all__ = [
    "DemoStoreAdapter",
    "IntegrationConfigError",
    "IntegrationError",
    "ShopifyAdapter",
    "SimulatedShopifyAdapter",
    "StoreIntegration",
    "TikTokShopAdapter",
    "get_store_integration",
    "record_tiktok_shop_webhook_event",
    "record_webhook_event",
    "verify_tiktok_shop_webhook",
    "verify_webhook_hmac",
]

log = logging.getLogger(__name__)


def get_store_integration(
    settings: "Settings", conn: sqlite3.Connection, store_id: str
) -> StoreIntegration:
    """Build the configured store backend for one pipeline run."""
    backend = (settings.store_backend or "demo").strip().lower()
    if backend == "shopify_simulated":
        return SimulatedShopifyAdapter(conn, store_id)
    if backend == "tiktok_shop":
        try:
            return TikTokShopAdapter(settings, store_id)
        except IntegrationConfigError as exc:
            # "not configured": report honestly, keep serving via demo.
            log.warning(
                "TikTok-Shop-Backend nicht konfiguriert (%s) — falle "
                "auf Demo-Backend zurück.",
                exc,
            )
            return DemoStoreAdapter(conn, store_id)
    # "demo" default; unknown values fall back to demo (never crash prod).
    return DemoStoreAdapter(conn, store_id)
