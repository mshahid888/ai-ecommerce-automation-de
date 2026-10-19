"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_LINKS, isNavActive } from "./Sidebar";

/** Kompakte horizontale Navigation für die mobile Kopfzeile (Desktop nutzt die Sidebar). */
export default function Nav() {
  const pathname = usePathname();

  return (
    <nav aria-label="Hauptnavigation">
      <ul className="flex items-center gap-1">
        {NAV_LINKS.map(({ href, label, Icon }) => {
          const active = isNavActive(pathname, href);
          return (
            <li key={href}>
              <Link
                href={href}
                aria-current={active ? "page" : undefined}
                className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  active
                    ? "bg-blue-50 text-blue-700"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                <Icon className="h-4 w-4" />
                {label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
