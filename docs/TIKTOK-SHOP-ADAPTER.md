# TikTok-Shop-Adapter

Echter Adapter für die **TikTok Shop Open Platform** (REST-API für
Bestellungen und Produkte). Er implementiert das
`StoreIntegration`-Interface: Der Chat-Pipeline, dem Dashboard und der
Retouren-Triage ist egal, woher eine Bestellung kommt — TikTok Shop
wird wie jeder andere Shop auf das kanonische Datenmodell abgebildet.

**Status:** implementiert, offline getestet. Noch **kein echter Shop**
verbunden — erst nach ausdrücklicher Freigabe.

## Was der Adapter tut

- **Bestellungen lesen:** Suche per Bestell-ID (`/order/202309/orders/search`),
  Details inkl. Zahlungsbetrag, Währung und — falls vorhanden —
  Paket-/Tracking-Informationen.
- **Produkte lesen/suchen:** `/product/202309/products/...`
  (Titel, Beschreibung, Seller-SKU).
- **Status-Mapping (ehrlich dokumentiert):**

  | TikTok-Shop-Status   | Kanonischer Status |
  |----------------------|--------------------|
  | UNPAID               | processing         |
  | AWAITING_SHIPMENT    | processing         |
  | AWAITING_COLLECTION  | processing         |
  | PARTIALLY_SHIPPED    | shipped            |
  | IN_TRANSIT           | shipped            |
  | DELIVERED            | delivered          |
  | COMPLETED            | delivered          |
  | CANCELLED            | cancelled          |
  | unbekannt            | processing         |

  Anders als bei Shopify/WooCommerce meldet TikTok Shop echte
  Zustellungen — `DELIVERED → delivered` ist daher ehrlich, nicht
  geraten. `COMPLETED` bedeutet „zugestellt + 14 Tage ohne Retoure“.
  `eta_date` ist immer `None` (kein Liefertermin-Feld in der API).
- **Webhooks:** `POST /api/integrations/tiktok-shop/webhooks`.
  Signaturprüfung per HMAC-SHA256 (hex) über `app_key + Roh-Body` mit
  `app_secret`, verglichen mit dem `authorization`-Header (konstante
  Zeit). Idempotenz über `tts_notification_id`
  (`INSERT OR IGNORE`). Unbekannte Topics werden als „unhandled“
  protokolliert, aber mit 200 bestätigt (keine Retry-Stürme).
  Fehlerhafte Bodies lassen den Endpoint nie abstürzen.
  Webhooks werden nur **protokolliert** — keine automatischen
  Geschäftsaktionen.

## Marktplatz-Realität (wichtig)

TikTok Shop verkauft **in der App**. Unser Chat-Widget kann dort
**nicht** eingebettet werden. Kundennachrichten laufen über TikTok
Shops eigene Kundenservice-/IM-APIs und deren Richtlinien. Dieser
Adapter deckt die **Backend-Datensynchronisation** ab (Bestellungen
und Produkte für Pipeline + Dashboard). In-App-Messaging-Automatisierung
ist bewusst **nicht** enthalten — keine Workarounds um
Plattformregeln.

## Einrichtung (Händler-Seite)

1. **TikTok Shop Partner Center:** als Developer registrieren,
   Region/Markt wählen.
2. **App erstellen** („App & Service" → Custom App für den eigenen
   Shop), benötigte Scopes beantragen (Bestellungen, Produkte,
   Webhooks) und das App-Review abwarten (ca. 2–3 Werktage; Sandbox
   vorher testen).
3. **OAuth durchlaufen:** App Key → Autorisierungs-URL → Seller
   genehmigt → Code gegen `access_token` + `refresh_token` +
   Shop-Cipher tauschen. Token-Ablauf einplanen (Refresh vor Ablauf).
4. **Webhook-URL** in der App hinterlegen
   (`https://<backend>/api/integrations/tiktok-shop/webhooks`),
   Events abonnieren (z. B. Order-Status-Änderungen).
5. **Backend-`.env`** (Server, `chmod 600`, niemals committen):

   ```env
   STORE_BACKEND=tiktok_shop
   TIKTOK_SHOP_APP_KEY=<app key aus dem Partner Center>
   TIKTOK_SHOP_APP_SECRET=<app secret>
   TIKTOK_SHOP_ACCESS_TOKEN=<oauth access token>
   TIKTOK_SHOP_SHOP_ID=<shop cipher>
   # optional:
   TIKTOK_SHOP_BASE_URL=https://open-api.tiktokglobalshop.com
   TIKTOK_SHOP_WEBHOOK_SECRET=<app secret, falls abweichend>
   ```

   Fehlt eine Variable, meldet der Adapter ehrlich
   „nicht konfiguriert" und die Factory fällt auf das Demo-Backend
   zurück — der Chat läuft weiter.

## Sicherheit

- Secrets nur via Umgebungsvariablen; nie geloggt, nie in
  API-Antworten.
- Webhook-Signaturen werden mit `hmac.compare_digest` verglichen;
  fehlende/ungültige Signaturen → 401 + Audit-Eintrag.
- 10 s Timeout, max. 2 Retries mit Backoff; HTTP 429 beachtet
  `Retry-After` (max. 10 s).

## Grenzen (ehrlich)

- Request-Signatur (`sign`-Parameter) folgt dem dokumentierten
  Muster — **vor dem ersten Live-Betrieb gegen eine Dev-App
  validieren**.
- Tracking/Carrier nur, wenn TikTok Paketdaten liefert; sonst ehrlich
  „keine Angabe".
- Produktattribute (z. B. Spülmaschinenfestigkeit) kennt TikTok so
  nicht — die Pipeline antwortet ehrlich „keine Information".
- Kein In-App-Messaging (siehe oben).
