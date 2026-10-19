"use client";

import Link from "next/link";
import { useEffect, useState, type ComponentType } from "react";
import { ChatIcon, TicketIcon } from "@/components/Sidebar";
import {
  getDashboardSummary,
  type DashboardSummary,
} from "@/lib/api";

function formatDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString("de-DE");
}

function MessagesIcon({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-5l-5 5v-5Z" />
    </svg>
  );
}

function EscalationIcon({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5" />
    </svg>
  );
}

const CARD_DEFS: {
  key: "conversations_count" | "messages_count" | "tickets_open" | "escalations_count";
  label: string;
  description: string;
  Icon: ComponentType<{ className?: string }>;
  tint: string;
}[] = [
  {
    key: "conversations_count",
    label: "Unterhaltungen",
    description: "Chat-Unterhaltungen in der Demo-Datenbank",
    Icon: ChatIcon,
    tint: "bg-blue-100 text-blue-700",
  },
  {
    key: "messages_count",
    label: "Nachrichten",
    description: "Kunden- und Assistentennachrichten",
    Icon: MessagesIcon,
    tint: "bg-blue-100 text-blue-700",
  },
  {
    key: "tickets_open",
    label: "Offene Tickets",
    description: "Supportfälle mit Mitarbeiterbedarf",
    Icon: TicketIcon,
    tint: "bg-amber-100 text-amber-700",
  },
  {
    key: "escalations_count",
    label: "Eskalationen",
    description: "Explizite Übergaben an Mitarbeiter",
    Icon: EscalationIcon,
    tint: "bg-slate-100 text-slate-600",
  },
];

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [backendDown, setBackendDown] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getDashboardSummary()
      .then((data) => {
        if (!cancelled) setSummary(data);
      })
      .catch(() => {
        if (!cancelled) setBackendDown(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const maxIntentCount = Math.max(
    0,
    ...(summary?.intents_breakdown.map((b) => b.count) ?? []),
  );
  const totalIntents =
    summary?.intents_breakdown.reduce((sum, row) => sum + row.count, 0) ?? 0;

  return (
    <div className="space-y-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-widest text-blue-600">
          Übersicht
        </p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900">
          Dashboard
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          Betriebsübersicht für den Demo-Shop – alle Zahlen stammen aus der
          Datenbank und sind als{" "}
          <span className="font-medium">Demo-Daten</span> gekennzeichnet.
        </p>
      </div>

      {loading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4" aria-hidden="true">
          {CARD_DEFS.map((card) => (
            <div
              key={card.key}
              className="animate-pulse rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
            >
              <div className="h-10 w-10 rounded-xl bg-slate-100" />
              <div className="mt-4 h-8 w-20 rounded bg-slate-100" />
              <div className="mt-2 h-4 w-28 rounded bg-slate-100" />
            </div>
          ))}
        </div>
      )}

      {!loading && backendDown && (
        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 shadow-sm"
        >
          Das Backend ist nicht erreichbar – Kennzahlen können derzeit nicht
          angezeigt werden.
        </div>
      )}

      {!loading && !backendDown && summary && (
        <>
          <section aria-label="Kennzahlen">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {CARD_DEFS.map((card) => (
                <div
                  key={card.key}
                  className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md"
                >
                  <div className="flex items-center justify-between">
                    <span
                      className={`flex h-10 w-10 items-center justify-center rounded-xl ${card.tint}`}
                    >
                      <card.Icon className="h-5 w-5" />
                    </span>
                    <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                      Demo-Daten
                    </span>
                  </div>
                  <p className="mt-4 text-3xl font-semibold tabular-nums tracking-tight text-slate-900">
                    {summary[card.key]}
                  </p>
                  <p className="mt-1 text-sm font-medium text-slate-700">
                    {card.label}
                  </p>
                  <p className="mt-0.5 text-xs text-slate-500">
                    {card.description}
                  </p>
                </div>
              ))}
            </div>
            <p className="mt-3 text-xs text-slate-500">
              Tickets gesamt:{" "}
              <span className="font-medium tabular-nums text-slate-700">
                {summary.tickets_total}
              </span>{" "}
              (Demo-Daten) ·{" "}
              <Link
                href="/tickets"
                className="font-medium text-blue-700 underline underline-offset-2"
              >
                Alle Tickets ansehen
              </Link>
            </p>
          </section>

          <section
            aria-label="Anliegen-Verteilung"
            className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
          >
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 className="text-lg font-semibold tracking-tight text-slate-900">
                Anliegen-Verteilung
              </h2>
              {totalIntents > 0 && (
                <span className="text-xs font-medium tabular-nums text-slate-500">
                  {totalIntents} erkannt
                </span>
              )}
            </div>
            <p className="mt-1 text-sm text-slate-600">
              Erkannte Absichten aus echten Chat-Unterhaltungen.{" "}
              <span className="font-medium">Demo-Daten</span> – keine
              Geschäftsauswertung.
            </p>
            {summary.intents_breakdown.length === 0 ? (
              <div className="mt-4 rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center">
                <p className="text-sm text-slate-600">
                  Noch keine Unterhaltungen vorhanden. Starten Sie eine
                  Unterhaltung auf der{" "}
                  <Link href="/" className="font-medium text-blue-700 underline">
                    Chat-Seite
                  </Link>
                  , um die Verteilung zu sehen.
                </p>
              </div>
            ) : (
              <div className="mt-5 space-y-4">
                {summary.intents_breakdown.map((row) => {
                  const pct =
                    totalIntents > 0
                      ? Math.round((row.count / totalIntents) * 100)
                      : 0;
                  return (
                    <div key={row.intent}>
                      <div className="flex items-baseline justify-between text-sm">
                        <span className="font-medium text-slate-800">
                          {row.label_de}
                        </span>
                        <span className="tabular-nums text-slate-600">
                          {row.count}
                          <span className="ml-1.5 text-xs text-slate-400">
                            {pct}%
                          </span>
                        </span>
                      </div>
                      <div
                        role="img"
                        aria-label={`${row.label_de}: ${row.count}`}
                        className="mt-1.5 h-2.5 overflow-hidden rounded-full bg-slate-100"
                      >
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-blue-500 to-blue-600 transition-all"
                          style={{
                            width: `${
                              maxIntentCount > 0
                                ? Math.max(
                                    4,
                                    Math.round(
                                      (row.count / maxIntentCount) * 100,
                                    ),
                                  )
                                : 0
                            }%`,
                          }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          <section aria-label="Letzte Aktivitäten">
            <h2 className="text-lg font-semibold tracking-tight text-slate-900">
              Letzte Aktivitäten
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              Tatsächlich ausgeführte Workflow-Schritte – jeder Eintrag
              entspricht einer Operation im Backend.
            </p>
            {summary.recent_events.length === 0 ? (
              <div className="mt-4 rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center">
                <p className="text-sm text-slate-600">
                  Noch keine Aktivitäten protokolliert.
                </p>
              </div>
            ) : (
              <ol className="mt-4 space-y-2">
                {summary.recent_events.map((event) => (
                  <li
                    key={event.id}
                    className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm transition-colors hover:border-blue-200"
                  >
                    <span
                      className={`h-2 w-2 shrink-0 rounded-full ${
                        event.status === "failed" ? "bg-red-500" : "bg-green-500"
                      }`}
                      aria-hidden="true"
                    />
                    <span className="min-w-0 flex-1 font-medium text-slate-800">
                      {event.label_de}
                      {event.status === "failed" && (
                        <span className="ml-2 rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-800">
                          Fehlgeschlagen
                        </span>
                      )}
                    </span>
                    <span className="shrink-0 text-xs tabular-nums text-slate-500">
                      {formatDate(event.created_at)}
                    </span>
                  </li>
                ))}
              </ol>
            )}
          </section>

          <section
            aria-label="Sicherheit und Datenschutz (Demo)"
            className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
          >
            <h2 className="text-lg font-semibold tracking-tight text-slate-900">
              Sicherheit &amp; Datenschutz (Demo)
            </h2>
            <ul className="mt-3 list-none space-y-2.5 pl-0 text-sm text-slate-700">
              <li className="flex items-start gap-2.5"><span aria-hidden="true" className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-green-100 text-xs font-bold text-green-700">✓</span><span>
                <span className="font-medium">Simulierte Daten:</span>{" "}
                Alle Bestellungen, Produkte und Kunden in dieser Demo sind
                frei erfunden. Es werden keine echten Bestellungen
                verarbeitet und keine echten Retouren oder
                Rückerstattungen ausgeführt.
              </span></li>
              <li className="flex items-start gap-2.5"><span aria-hidden="true" className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-green-100 text-xs font-bold text-green-700">✓</span><span>
                <span className="font-medium">Keine echten Zahlungen:</span>{" "}
                Die Demo fragt keine Zahlungsdaten ab und speichert keine
                personenbezogenen Daten echter Kunden.
              </span></li>
              <li className="flex items-start gap-2.5"><span aria-hidden="true" className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-green-100 text-xs font-bold text-green-700">✓</span><span>
                <span className="font-medium">Nutzungsbegrenzung:</span>{" "}
                Anfragen sind pro Besucher begrenzt (Chat, Leserequests und
                Demo-Zurücksetzung). Bei Überschreitung antwortet das
                Backend mit HTTP&nbsp;429 und einer Wartezeit.
              </span></li>
              <li className="flex items-start gap-2.5"><span aria-hidden="true" className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-green-100 text-xs font-bold text-green-700">✓</span><span>
                <span className="font-medium">KI-Kontingent:</span> Die
                Anzahl echter KI-Anfragen pro Tag ist gedeckelt. Ist das
                Kontingent aufgebraucht, antwortet das Demo-Regelwerk —
                das wird in der Unterhaltung ehrlich gekennzeichnet.
              </span></li>
              <li className="flex items-start gap-2.5"><span aria-hidden="true" className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-green-100 text-xs font-bold text-green-700">✓</span><span>
                <span className="font-medium">Admin-Schutz:</span>{" "}
                Das Zurücksetzen der Demo erfordert einen serverseitigen
                Admin-Schlüssel. Sicherheitsrelevante Ereignisse
                (z.&nbsp;B. fehlgeschlagene Admin-Versuche) werden in einem
                unveränderlichen Audit-Protokoll festgehalten.
              </span></li>
            </ul>
          </section>
        </>
      )}
    </div>
  );
}
