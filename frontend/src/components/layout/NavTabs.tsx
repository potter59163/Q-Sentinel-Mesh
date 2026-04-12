"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { getAllowedTabs, getStoredAuth, type UserRole } from "@/lib/auth";

const ALL_TABS = [
  { href: "/dashboard",           label: "🧠 Diagnostic View" },
  { href: "/dashboard/federated", label: "🌐 Federated Intelligence" },
  { href: "/dashboard/security",  label: "🔒 Security Layer" },
  { href: "/dashboard/pacs",      label: "🏥 PACS Integration" },
];

export default function NavTabs() {
  const pathname = usePathname();
  const [allowedTabs, setAllowedTabs] = useState<string[]>(ALL_TABS.map((t) => t.href));

  useEffect(() => {
    const auth = getStoredAuth();
    if (auth) setAllowedTabs(getAllowedTabs(auth.role as UserRole));
  }, []);

  const visibleTabs = ALL_TABS.filter((t) => allowedTabs.includes(t.href));

  return (
    <nav className="q-nav-underline">
      {visibleTabs.map((tab) => {
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
