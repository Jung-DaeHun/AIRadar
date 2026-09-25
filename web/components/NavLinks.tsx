"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS: [string, string][] = [
  ["/news", "뉴스"],
  ["/tools", "도구 추천"],
  ["/trending", "급상승"],
];

export default function NavLinks() {
  const pathname = usePathname();
  return (
    <nav className="flex gap-4 text-sm">
      {LINKS.map(([href, label]) => {
        const active = pathname === href || pathname.startsWith(`${href}/`);
        return (
          <Link
            key={href}
            href={href}
            aria-current={active ? "page" : undefined}
            className={active ? "font-semibold text-foreground" : "text-muted hover:text-foreground"}
          >
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
