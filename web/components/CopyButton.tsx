"use client";

import { useState } from "react";

export default function CopyButton({ text }: { text: string }) {
  const [status, setStatus] = useState<"idle" | "copied" | "failed">("idle");
  return (
    <button
      type="button"
      aria-label="설치 명령 복사"
      className="flex shrink-0 items-center gap-1 rounded-md px-2 py-1 text-xs text-muted hover:bg-background hover:text-foreground"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setStatus("copied");
        } catch {
          setStatus("failed");
        }
        setTimeout(() => setStatus("idle"), 1500);
      }}
    >
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <rect x="9" y="9" width="13" height="13" rx="2" />
        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
      </svg>
      {status === "copied" && <span className="text-accent">복사됨</span>}
      {status === "failed" && <span>복사 실패</span>}
    </button>
  );
}
