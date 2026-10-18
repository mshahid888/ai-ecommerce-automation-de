# Shopify-Adapter (echt) — Einrichtung & Betrieb

**Stand: Phase 9b (2026-10-18).** Der `ShopifyAdapter` (`backend/app/integrations/shopify.py`)
implementiert das `StoreIntegration`-Interface gegen die echte Shopify Admin API
(REST, API-Version `2026-10`). Alle HTTP-Aufrufe sind in Tests gemockt —
**es wurde noch nie ein echter Shopify-Shop angebunden, kein Dev-Store, keine
Credentials.** Die Pipeline nutzt den Adapter nur, wenn er konfiguriert ist;
sonst fällt sie still auf den Demo-Adapter zurück.

## 1. Was der Adapter tut

- **Bestellungen lesen:** `GET /orders.json?name=%2310482&status=any` — Suche über
  die kaufmännische Bestellnummer (`name`, z. B. `#10482`). Nicht gefunden →
  ehrliches „nicht gefunden" (kein Erfinden).
- **Produkte lesen/suchen:** `GET /products/{id}.json` bzw.
  `GET /products.json?title=…`; SKU-Suche über Trefferabgleich.
- **Versandinfos:** `GET /orders/{id}/fulfillments.json` → `tracking_number`,
  `tracking_company`. Gibt es keine Sendungsdaten, liefert der Adapter ehrlich
  `None` (die Pipeline sagt dann „noch keine Versandinformationen").
- **Webhooks:** `POST /api/integrations/shopify/webhooks` verifiziert
  HMAC-SHA256, dedupliziert über `X-Shopify-Webhook-Id` und protokolliert
  `orders/create`, `orders/updated`, `refunds/create` im Audit-Log.
  Es werden nur Zustellungen *protokolliert* — keine automatischen
  Bestell-/Erstattungsaktionen.

## 2. Status-Mapping (Shopify → kanonisch)

| Shopify-Signal                     | Kanonischer Status |
|------------------------------------|--------------------|
| Bestellung `cancelled = true`      | `cancelled`        |
| `fulfillment_status = fulfilled`   | `shipped`          |
| `fulfillment_status = partial`     | `processing`       |
| `fulfillment_status = unfulfilled` | `processing`       |
| `fulfillment_status = restocked`   | `processing`       |
| `fulfillment_status = null`/andere | `processing`       |

Ehrliche Grenzen: Die REST-API liefert **kein verlässliches
„delivered"-Signal** und kennt kein „delayed" — der Adapter emittiert diese
Status nie (kein Raten). `eta_date` ist immer `None`; die Pipeline lässt die
Lieferprognose dann weg. Produktattribute (z. B. Spülmaschinenfestigkeit)
haben kein Shopify-Äquivalent — `attributes_json` ist `{}`, die Pipeline
antwortet ehrlich „keine Information vorhanden".

## 3. Benötigte Umgebungsvariablen (Backend-`.env`, niemals committen)

| Variable                  | Pflicht      | Zweck                                        |
|---------------------------|--------------|----------------------------------------------|
| `SHOPIFY_SHOP_DOMAIN`     | ja           | `dein-shop.myshopify.com` (nur die Domain)   |
| `SHOPIFY_ADMIN_TOKEN`     | ja           | Admin-API-Zugriffstoken der Custom App       |
| `SHOPIFY_ADMIN_API_TOKEN` | nein         | alte Variable, wird weiterhin akzeptiert     |
| `SHOPIFY_API_VERSION`     | nein         | Standard `2026-10`                           |
| `SHOPIFY_WEBHOOK_SECRET`  | für Webhooks | Client-Secret der Custom App (HMAC-Prüfung)  |
| `STORE_BACKEND`           | nein         | `shopify` wählen; ohne Konfiguration → Demo  |

Fehlt die Konfiguration, meldet der Adapter „nicht konfiguriert" und die
Pipeline nutzt automatisch den Demo-Adapter weiter — nichts stürzt ab.

## 4. Custom App im Shopify-Admin anlegen (kostenlos)

1. Unter partners.shopify.com kostenloses Partnerkonto erstellen
   (falls nicht vorhanden).
2. **Stores → Add store → Development store** — einen Dev-Store anlegen
   (kein echter Shop, keine Kosten).
3. Im Dev-Store: **Einstellungen → Apps und Vertriebskanäle → App entwickeln**
   (ggf. erst „Custom App-Entwicklung zulassen" aktivieren).
4. App-Name vergeben, z. B. `Demo-Support-Agent`.
5. **Konfiguration → Admin-API-Bereiche:** `read_orders`, `read_products`,
   `read_fulfillments` aktivieren → speichern.
6. **API-Zugangsdaten → Admin-API-Zugriffstoken → Token installieren.**
   Das Token wird nur **einmal** angezeigt — sofort in die Backend-`.env`
   als `SHOPIFY_ADMIN_TOKEN=…` eintragen. Datei mit `chmod 600` schützen,
   niemals committen, niemals per Chat/E-Mail verschicken.
7. In derselben Ansicht steht das **Client-Geheimnis** → als
   `SHOPIFY_WEBHOOK_SECRET=…` in die `.env` eintragen.
8. `SHOPIFY_SHOP_DOMAIN=<dev-store>.myshopify.com` und optional
   `STORE_BACKEND=shopify` setzen → Backend neu starten.

## 5. Webhooks registrieren

Im Shopify-Admin des Dev-Stores: **Einstellungen → Benachrichtigungen →
Webhooks → Webhook erstellen:**

| Ereignis         | Format | URL                                                     |
|------------------|--------|---------------------------------------------------------|
| `orders/create`  | JSON   | `https://<dein-host>/api/integrations/shopify/webhooks` |
| `orders/updated` | JSON   | `https://<dein-host>/api/integrations/shopify/webhooks` |
| `refunds/create` | JSON   | `https://<dein-host>/api/integrations/shopify/webhooks` |

API-Version: die unter `SHOPIFY_API_VERSION` eingestellte (Standard `2026-10`).
Jede Zustellung wird per HMAC verifiziert (401 bei falscher Signatur),
über die Webhook-ID dedupliziert und im Audit-Log protokolliert.

## 6. Grenzen (ehrlich)

- **Kein echter Shop verbunden:** Ohne Dev-Store + Token passiert nichts —
  der Adapter meldet „nicht konfiguriert", die Demo läuft weiter.
- **Nur Lesen:** Der Adapter liest Bestellungen/Produkte/Fulfillments. Er
  erstellt keine Bestellungen, löst keine Erstattungen aus, ändert nichts
  im Shop.
- **Keine Lieferprognose:** `eta_date` ist immer `None`.
- **Keine Produktattribute:** `attributes_json` ist `{}`.
- **Antworten auf Deutsch:** Die Pipeline antwortet in der Sprache des
  Repos (dieses Repo: Deutsch).
- **Rate-Limits:** 10 s Timeout pro Request, 2 Wiederholungen mit Backoff;
  HTTP 429 beachtet `Retry-After` (max. 10 s).

## 7. Sicherheit

- Token und Webhook-Secret nur in Server-Umgebungsvariablen / `.env`
  (`chmod 600`); **niemals** committen, loggen oder an die Pipeline
  zurückgeben.
- Webhook-Signaturen werden mit `hmac.compare_digest` (konstantzeitig)
  geprüft; ungültige Signaturen → 401 + Audit-Eintrag.
- Der Admin-API-Token braucht nur die drei Lese-Scopes — keine
  Schreibrechte vergeben.
