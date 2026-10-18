# Etsy-Adapter (Etsy Open API v3)

Echter Etsy-Adapter für die AI-E-Commerce-Automation-Plattform.
Implementiert das `StoreIntegration`-Interface gegen die Etsy Open API v3.
Alle HTTP-Aufrufe sind in Tests gemockt — es gab nie einen echten
API-Aufruf.

## Was der Adapter tut

- **Bestellungen**: Abruf einzelner Etsy-Receipts
  (`GET /v3/application/shops/{shop_id}/receipts/{receipt_id}`) sowie
  Auflistung (`.../receipts`). Die Händler-Referenz auf Etsy ist die
  numerische `receipt_id` (z. B. `#1234567890`).
- **Produkte**: Suche in aktiven Listings des Shops
  (`GET /v3/application/listings/active?keywords=…&shop_id=…`),
  Einzelabruf per `listing_id`.
- **Normalisierung**: Etsy-Daten werden in das kanonische Format der
  Plattform übersetzt (order_ref, status, total_cents, currency …).
  Was Etsy nicht liefert (Tracking, Liefertermin, SKU auf Listings),
  bleibt ehrlich `None`/`{}` — die Pipeline erfindet keine Angaben.

## Status-Mapping (ehrlich dokumentiert)

Etsy-Receipts kennen nur `was_paid` / `was_shipped`. Es gibt **kein**
delivered/delayed/cancelled-Signal — der Adapter erfindet diese
Status nie.

| Etsy-Signal                              | kanonischer Status |
|------------------------------------------|--------------------|
| `was_shipped = true`                     | `shipped`          |
| `was_shipped = false`, `was_paid = true` | `processing`       |
| `was_paid = false`                       | `processing`       |
| Flags fehlen / unbekannt                 | `processing`       |

## Einrichtung (Händler)

1. Im [Etsy Developer Portal](https://www.etsy.com/developers) eine App
   anlegen → **API-Key** kopieren.
2. Für Bestelldaten (Receipts) zusätzlich **OAuth 2.0** einrichten und
   ein Token mit Shop-Lesezugriff erzeugen → `ETSY_OAUTH_TOKEN`.
   Ohne OAuth-Token antwortet die API mit 401/403; der Adapter meldet
   dann eine deutsche Anleitung statt still leerer Ergebnisse.
3. **Shop-ID** aus dem Shop-Manager übernehmen (Ziffern in der
   Shop-URL bzw. Shop-Einstellungen).
4. In der Backend-`.env` (niemals committen, `chmod 600`):

```env
STORE_BACKEND=etsy
ETSY_API_KEY=<api-key>
ETSY_SHOP_ID=<shop-id-nummer>
ETSY_OAUTH_TOKEN=<oauth-token>   # für Receipts nötig
```

5. Backend neu starten. Ohne Konfiguration meldet der Adapter
   `IntegrationConfigError` (deutsch) und die Factory fällt automatisch
   auf das Demo-Backend zurück — die Pipeline läuft immer.

## Messaging-Realität (wichtig)

Etsy erlaubt **kein** Einbetten eines fremden Chat-Widgets auf
etsy.com-Seiten. Käufer↔Verkäufer-Nachrichten laufen über Etsys
eigenes "Convos"-System unter Etsys Regeln. Dieser Adapter deckt
daher **nur die Backend-Datensynchronisation** ab (Bestellungen und
Produkte für Pipeline + Dashboard). Das automatisierte Lesen oder
Senden von Convos-Nachrichten ist bewusst **außerhalb des Umfangs** —
Nachrichten-Automatisierung außerhalb der Etsy-Regeln gefährdet den
Shop des Händlers.

## Sicherheit

- Secrets nur via Umgebungsvariablen; `.env` ist git-ignoriert.
- API-Key/OAuth-Token nur im Speicher, nie in Logs oder Antworten.
- 10 s Timeout, 2 Retries mit Backoff; 429 respektiert `Retry-After`.
- 401/403 → deutsche Anleitung (meist: OAuth-Token/Scopes prüfen).

## Grenzen

- Kein Tracking, kein Liefertermin, keine SKU auf Listings (ehrlich
  `None`/`{}`).
- Keine Webhooks: Die Etsy-API bietet keine öffentlichen Shop-Webhooks;
  Synchronisation läuft per Abruf.
- `delivered`/`delayed`/`cancelled` werden nie gemeldet.
- Erst gegen einen echten Test-Shop verifizieren, bevor ein
  Produktiv-Shop angebunden wird — nur mit Shahids schriftlicher
  Freigabe.
