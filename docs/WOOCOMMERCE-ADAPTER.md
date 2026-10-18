# WooCommerce-Adapter (echt) — Einrichtung & Betrieb

Echter WooCommerce-REST-API-Adapter (`WooCommerceAdapter`) für die
AI-E-Commerce-Automation-Plattform. Offline getestet (31 Tests, alle
HTTP-Aufrufe gemockt) — **noch nie gegen einen echten Shop gelaufen**.
Erst gegen einen Test-Shop verifizieren, bevor ein Händler-Shop
angebunden wird.

## 1. Was der Adapter tut

- `get_order("#12345")` — Bestellung per WooCommerce-Bestellnummer laden
  (`GET /wp-json/wc/v3/orders/{id}`). WooCommerce-Bestellnummern sind
  standardmäßig numerische IDs (`#12345` und `12345` funktionieren beide;
  individuelle Bestellnummern-Plugins werden nicht unterstützt).
- `get_product()` / `search_products()` — Produkte per ID, SKU oder
  Volltextsuche (`/wp-json/wc/v3/products`).
- `get_fulfillment()` — Tracking-/Versandinfos aus Bestell-Meta-Feldern
  (Versand-Plugins), falls vorhanden.
- `list_orders()` — neueste Bestellungen (max. 100 pro Abruf).
- Webhook-Endpunkt `POST /api/integrations/woocommerce/webhooks` für
  `order.created` / `order.updated` — nur Protokollierung (idempotent),
  keine automatischen Geschäftsaktionen.

## 2. Status-Mapping (WooCommerce → kanonisch)

| WooCommerce-Status | Kanonisch     | Begründung                              |
|--------------------|---------------|-----------------------------------------|
| `pending`          | `processing`  | wartet auf Zahlung                       |
| `processing`       | `processing`  |                                          |
| `on-hold`          | `processing`  | wartet auf manuelle Aktion               |
| `completed`        | `shipped`     | Konvention: erfüllt/versendet (s. unten) |
| `cancelled`        | `cancelled`   |                                          |
| `refunded`         | `cancelled`   | Endzustand, wie storniert                |
| `failed`           | `cancelled`   | Zahlung fehlgeschlagen — nie erfüllt     |
| `trash`            | `cancelled`   |                                          |
| unbekannt          | `processing`  | sicherer Standardwert                    |

**Ehrlich dokumentiert:** WooCommerce kennt keinen nativen
„shipped"-Status — `completed` → `shipped` ist eine Konvention, keine
Garantie (manche Shops setzen `completed` schon bei Zahlungseingang).
`delivered` und `delayed` werden **niemals erfunden**: WooCommerce liefert
kein verlässliches Signal dafür. Ebenso gibt es kein natives
Sendungsverfolgungs-Feld — Tracking kommt nur aus Meta-Feldern von
Versand-Plugins (`_tracking_number` u. ä.); ohne diese bleibt
`tracking_ref` leer und die Pipeline sagt das ehrlich.

## 3. Benötigte Umgebungsvariablen (Backend-`.env`, niemals committen)

```bash
STORE_BACKEND=woocommerce
WOOCOMMERCE_SHOP_URL=https://example-shop.de   # NUR https (Pflicht)
WOOCOMMERCE_CONSUMER_KEY=ck_...
WOOCOMMERCE_CONSUMER_SECRET=cs_...
WOOCOMMERCE_WEBHOOK_SECRET=whsec_...           # nur für Webhooks nötig
```

Fehlt die Konfiguration, meldet die Factory eine deutsche Warnung und
fällt still auf das Demo-Backend zurück — die Pipeline läuft weiter.

## 4. REST-API-Schlüssel erzeugen (kostenlos)

1. Im WordPress-Backend: **WooCommerce → Einstellungen → Erweitert →
   REST-API → Schlüssel hinzufügen**.
2. Benutzer wählen, **Berechtigung „Lesen"** (reicht für diesen Adapter),
   **Schlüssel erzeugen**.
3. Consumer Key + Consumer Secret in die Backend-`.env` eintragen
   (`chmod 600`), Backend neu starten.

## 5. Webhooks registrieren

1. **WooCommerce → Einstellungen → Erweitert → Webhooks → Webhook
   hinzufügen**: Thema `Bestellung erstellt` / `Bestellung aktualisiert`,
   Liefer-URL `https://<backend-domain>/api/integrations/woocommerce/webhooks`,
   ein starkes **Geheimnis** vergeben → als `WOOCOMMERCE_WEBHOOK_SECRET`
   in die `.env` eintragen.
2. Der Adapter prüft `X-WC-Webhook-Signature` (HMAC-SHA256, konstantzeit-
   Vergleich); doppelte `X-WC-Webhook-Delivery-ID`s werden genau einmal
   verarbeitet.
3. Ohne gesetztes Geheimnis antwortet der Endpunkt ehrlich mit 503
   (`woocommerce_not_configured`).

## 6. Grenzen (ehrlich)

- Kein Test gegen einen echten Shop erfolgt — Mapping-Tabelle und
  Meta-Felder müssen an einem Test-Shop verifiziert werden.
- Individuelle Bestellnummern-Plugins werden nicht unterstützt.
- Produktattribute kommen aus der WooCommerce-Attributliste; Shops ohne
  Attribute liefern `{}` (die Pipeline antwortet ehrlich).
- `eta_date` ist immer leer (kein WooCommerce-Feld dafür).
- Webhooks werden nur protokolliert, nicht verarbeitet.

## 7. Sicherheit

- Nur HTTPS (HTTP-URLs werden beim Start abgelehnt — sonst würden
  Schlüssel in Server-Logs landen).
- Schlüssel nur in Server-Umgebungsvariablen, niemals im Code/Frontend/Git.
- 10-s-Timeout, 2 Retries mit Backoff, `Retry-After` bei 429, keine
  Token-Weitergabe in Fehlermeldungen oder Payloads.
- Webhook-Signaturprüfung + Idempotenz + Audit-Log wie beim
  Shopify-Adapter.
