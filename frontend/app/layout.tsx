import type { Metadata } from "next";
import Nav from "@/components/Nav";
import Sidebar from "@/components/Sidebar";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI E-Commerce Automation – Muster-Shop GmbH",
  description:
    "Demo des KI-Kundenservice für die Muster-Shop GmbH: Bestellstatus, Produktfragen und Retouren-Triage.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="de" className="h-full">
      <body className="min-h-screen bg-white font-sans text-slate-900 antialiased">
        <Sidebar />

        <div className="lg:pl-64">
          {/* Mobile top bar */}
          <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur lg:hidden">
            <div className="flex items-center justify-between gap-3 px-4 py-3">
              <div className="flex items-center gap-2.5">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-xs font-bold text-white">
                  AI
                </span>
                <span className="text-sm font-semibold tracking-tight text-slate-900">
                  AI E-Commerce
                </span>
              </div>
              <Nav />
            </div>
          </header>

          {/* Desktop top bar */}
          <div className="hidden border-b border-slate-200 bg-white lg:block">
            <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
              <p className="text-sm text-slate-500">
                Demo-Shop:{" "}
                <span className="font-medium text-slate-700">
                  Muster-Shop GmbH
                </span>
              </p>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-800">
                <span
                  className="h-1.5 w-1.5 rounded-full bg-amber-500"
                  aria-hidden="true"
                />
                Demo-Umgebung
              </span>
            </div>
          </div>

          <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6">
            {children}
          </main>

          <footer className="border-t border-slate-200">
            <p className="mx-auto max-w-6xl px-4 py-4 text-xs text-slate-500 sm:px-6">
              Phase 6 – Demo mit echten Workflows: Bestellstatus, Produktkatalog
              und Retouren-Triage. Alle Daten sind simuliert; es werden keine
              echten Bestellungen verarbeitet.
            </p>
          </footer>
        </div>
      </body>
    </html>
  );
}
