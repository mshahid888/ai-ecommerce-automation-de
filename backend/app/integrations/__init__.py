"""Store integrations (Phase 9/9b): interface, adapters, factory.

``get_store_integration()`` is the single place that decides which
``StoreIntegration`` the pipeline uses. ``STORE_BACKEND`` (env):
``demo`` (default) → ``DemoStoreAdapter``;
``shopify_simulated`` → ``SimulatedShopifyAdapter``;
``shopify`` → ``ShopifyAdapter`` (real Admin API). When ``shopify``
is selected but ``SHOPIFY_*`` is not configured, the factory logs a
German warning and falls back to ``demo`` — the pipeline never
crashes on a missing shop configuration. Unknown values fall back to
``demo``.
"""

from __future__ import annotations

import logging
import sqlite3
from typing import TYPE_CHECKING

log = logging.getLogger(__name__)

from .base import (
    IntegrationConfigError,
    IntegrationError,
    StoreIntegration,
)
from .demo import DemoStoreAdapter
from .shopify import ShopifyAdapter
from .shopify_simulated import SimulatedShopifyAdapter
from .webhooks import record_webhook_event, verify_webhook_hmac

if TYPE_CHECKING:  # pragma: no cover
    from ..config import Settings

__all__ = [
    "DemoStoreAdapter",
    "IntegrationConfigError",
    "IntegrationError",
    "ShopifyAdapter",
    "SimulatedShopifyAdapter",
    "StoreIntegration",
    "get_store_integration",
    "record_webhook_event",
    "verify_webhook_hmac",
]


def get_store_integration(
    settings: "Settings", conn: sqlite3.Connection, store_id: str
) -> StoreIntegration:
    """Build the configured store backend for one pipeline run."""
    backend = (settings.store_backend or "demo").strip().lower()
    if backend == "shopify_simulated":
        return SimulatedShopifyAdapter(conn, store_id)
    if backend == "shopify":
        try:
            return ShopifyAdapter(settings, store_id)
        except IntegrationConfigError as exc:
            # "not configured": report honestly, keep serving via demo.
            log.warning(
                "Shopify-Backend nicht konfiguriert (%s) — falle auf "
                "Demo-Backend zurück.",
                exc,
            )
            return DemoStoreAdapter(conn, store_id)
    # "demo" default; unknown values fall back to demo (never crash prod).
    return DemoStoreAdapter(conn, store_id)
