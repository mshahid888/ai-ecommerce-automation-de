# eBay-Adapter (eBay Sell APIs)

Echter eBay-Adapter für die AI-E-Commerce-Automation-Plattform.
Implementiert das `StoreIntegration`-Interface gegen eBays Sell APIs
(Fulfillment API für Bestellungen, Inventory API für den
Händler-Katalog). Alle HTTP-Aufrufe sind in Tests gemockt — es gab nie
einen echten API-Aufruf.

## Was der Adapter tut

- **Bestellungen**: Abruf über die Fulfillment API
  (`GET /sell/fulfillment/v1/order/{orderId}`; eBay-IDs sehen aus wie
  `12-34567-89012`) sowie Auflistung (`.../order?limit=…`).
- **Produkte**: Der **eigene Händler-Katalog** über die Inventory API
  (`GET /sell/inventory/v1/inventory_item`, Einzel-SKU per
  `.../inventory_item/{sku}`).
- **Authentifizierung**: OAuth 2.0 Client-Credentials-Flow
  (`POST /identity/v1/oauth2/token`, Scopes `sell.fulfillment` +
  `sell.inventory`). Das Token wird im Speicher gecacht und vor Ablauf
  erneuert. Alternativ kann ein fertiges Token per `EBAY_OAUTH_TOKEN`
  übergeben werden.
- **Normalisierung**: eBay-Daten werden in das kanonische Format der
  Plattform übersetzt. Tracking kommt aus den Line-Items, wenn
  vorhanden — sonst ehrlich `None`.

## Status-Mapping (ehrlich dokumentiert)

Die Fulfillment API kennt nur `orderFulfillmentStatus`. Es gibt **kein**
delivered/delayed-Signal und keinen Stornierungs-Status (Stornos
laufen über einen separaten eBay-Flow) — der Adapter erfindet diese
Status nie.

| eBay-Signal              | kanonischer Status |
|--------------------------|--------------------|
| `FULFILLED`              | `shipped`          |
| `IN_PROGRESS`            | `processing`       |
| `NOT_STARTED`            | `processing`       |
| fehlt / unbekannt        | `processing`       |

## Einrichtung (Händler)

1. Im [eBay Developers Program](https://developer.ebay.com) eine App
   anlegen (Sandbox zum Testen, Produktion später).
2. **Client-ID** und **Client-Secret** kopieren; der App die Scopes
   `sell.fulfillment` und `sell.inventory` geben.
3. Marktplatz wählen (Standard: `EBAY_DE` für Deutschland).
4. In der Backend-`.env` (niemals committen, `chmod 600`):

```env
STORE_BACKEND=ebay
EBAY_CLIENT_ID=<client-id>
EBAY_CLIENT_SECRET=<client-secret>
EBAY_MARKETPLACE_ID=EBAY_DE        # optional, Standard ist EBAY_DE
# alternativ: EBAY_OAUTH_TOKEN=<fertiges-token>
```

5. Backend neu starten. Ohne Konfiguration meldet der Adapter
   `IntegrationConfigError` (deutsch) und die Factory fällt automatisch
   auf das Demo-Backend zurück — die Pipeline läuft immer.

## Messaging-Realität (wichtig)

eBay erlaubt **kein** Einbetten eines fremden Chat-Widgets auf
ebay.de-Artikelseiten. Käufer↔Verkäufer-Nachrichten laufen über eBays
eigenes Nachrichtensystem unter eBays Regeln. Dieser Adapter deckt
daher **nur die Backend-Datensynchronisation** ab (Bestellungen und
Produkte für Pipeline + Dashboard). Das automatisierte Lesen oder
Senden von eBay-Nachrichten ist bewusst **außerhalb des Umfangs** —
Nachrichten-Automatisierung außerhalb der eBay-Regeln gefährdet das
Verkäuferkonto.

## Sicherheit

- Secrets nur via Umgebungsvariablen; `.env` ist git-ignoriert.
- Client-Secret/OAuth-Token nur im Speicher, nie in Logs oder
  Antworten (Basic-Auth nur an den Token-Endpunkt).
- 10 s Timeout, 2 Retries mit Backoff; 429 respektiert `Retry-After`.
- 401 → deutsche Anleitung (Zugangsdaten/Scopes prüfen).

## Grenzen

- Kein Liefertermin (`eta_date` immer `None`); Tracking nur wenn die
  Line-Items es enthalten.
- `delivered`/`delayed`/`cancelled` werden nie gemeldet.
- Keine eBay-Webhooks implementiert (Notification API braucht
  Endpunkt-Validierung — als Folgeschritt dokumentiert, nicht
  hingehackt); Synchronisation läuft per Abruf.
- Erst gegen die eBay-Sandbox verifizieren, bevor ein Produktivkonto
  angebunden wird — nur mit Shahids schriftlicher Freigabe.
