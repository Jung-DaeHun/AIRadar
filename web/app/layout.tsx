import type { Metadata } from "next";
import Link from "next/link";
import InlineScript from "@/components/InlineScript";
import NavLinks from "@/components/NavLinks";
import ThemeToggle from "@/components/ThemeToggle";
import { getLastRuns } from "@/lib/db";
import { formatKst } from "@/lib/time";
import "./globals.css";

export const metadata: Metadata = { title: "Airadar", description: "AI 뉴스와 AI 코딩 도구 추천" };

// 렌더 전에 테마를 정해 새로고침 깜빡임을 막는다.
const themeScript = `(function(){var t;try{t=localStorage.getItem("theme")}catch(e){}if(t!=="light"&&t!=="dark"){t=matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"}document.documentElement.dataset.theme=t})()`;

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const runs = await getLastRuns();
  const news = runs.news && formatKst(runs.news);
  const repos = runs.repos && formatKst(runs.repos);
  const lastRun = [news && `뉴스 ${news}`, repos && `레포 ${repos}`].filter(Boolean).join(" · ");
  return (
    <html lang="ko" suppressHydrationWarning>
      <head>
        <InlineScript html={themeScript} />
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css"
        />
      </head>
      <body className="min-h-screen antialiased">
        <header className="sticky top-0 z-10 border-b border-line bg-background/80 backdrop-blur">
          <div className="mx-auto flex h-14 max-w-[720px] items-center gap-6 px-4">
            <Link href="/" className="text-lg font-bold tracking-tight">Airadar</Link>
            <NavLinks />
            <div className="ml-auto">
              <ThemeToggle />
            </div>
          </div>
        </header>
        {lastRun && (
          <p className="mx-auto max-w-[720px] px-4 pt-3 text-xs text-muted">마지막 수집 · {lastRun}</p>
        )}
        <main className="mx-auto max-w-[720px] px-4 py-10">{children}</main>
      </body>
    </html>
  );
}
