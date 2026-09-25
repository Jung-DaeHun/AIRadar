import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = { title: "Airadar", description: "AI 뉴스와 AI 코딩 도구 추천" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="mx-auto max-w-4xl px-4 py-6">
        <header className="mb-8 flex items-center gap-6">
          <Link href="/" className="text-xl font-bold">Airadar</Link>
          <nav className="flex gap-4 text-sm">
            <Link href="/news">뉴스</Link>
            <Link href="/tools">도구 추천</Link>
            <Link href="/trending">급상승</Link>
          </nav>
        </header>
        {children}
      </body>
    </html>
  );
}
