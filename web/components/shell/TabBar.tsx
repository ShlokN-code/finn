"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Briefcase, Newspaper, Search, SlidersHorizontal } from "lucide-react";

const TABS = [
  { href: "/brief", label: "Brief", Icon: Newspaper, match: (p: string) => p === "/" || p.startsWith("/brief") || p.startsWith("/e/") },
  { href: "/portfolio", label: "Portfolio", Icon: Briefcase, match: (p: string) => p.startsWith("/portfolio") },
  { href: "/research", label: "Research", Icon: Search, match: (p: string) => p.startsWith("/research") },
  { href: "/rules", label: "Rules", Icon: SlidersHorizontal, match: (p: string) => p.startsWith("/rules") || p.startsWith("/connect") },
];

export function TabBar() {
  return <Bar path={usePathname() ?? "/"} />;
}

/** Prerendered fallback (no active tab) while the pathname streams in. */
export function TabBarStatic() {
  return <Bar path="" />;
}

function Bar({ path }: { path: string }) {
  return (
    <nav aria-label="Main" className="grid grid-cols-4 border-t border-rule bg-paper">
      {TABS.map(({ href, label, Icon, match }) => {
        const on = match(path);
        return (
          <Link
            key={href}
            href={href}
            data-tour={href === "/research" ? "research-tab" : undefined}
            aria-current={on ? "page" : undefined}
            className={`relative flex h-14 flex-col items-center justify-center gap-0.5 text-[11px] ${
              on ? "font-semibold text-ink" : "text-ink-3"
            }`}
          >
            {on && <span aria-hidden className="absolute inset-x-6 top-0 h-0.5 bg-ink" />}
            <Icon className="size-[22px]" strokeWidth={on ? 2 : 1.5} />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
