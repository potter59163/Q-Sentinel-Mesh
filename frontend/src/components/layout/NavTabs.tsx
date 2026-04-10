"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/dashboard",            label: "🧠 Diagnostic View" },
  { href: "/dashboard/federated",  label: "🌐 Federated Intelligence" },
  { href: "/dashboard/security",   label: "🔒 Security Layer" },
];

export default function NavTabs() {
  const pathname = usePathname();

  return (
    <nav className="q-nav-underline">
      {TABS.map((tab) => {
        const active = pathname === tab.href;
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={`q-tab-ul ${active ? "q-tab-ul-active" : ""}`}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
