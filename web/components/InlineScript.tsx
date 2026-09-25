"use client";

// 서버 HTML에서는 실행되는 스크립트로, 클라이언트 렌더에서는 text/plain으로 둬서
// React의 "Encountered a script tag" 경고를 피한다. (Next 문서: preventing-flash-before-hydration)
export default function InlineScript({ html }: { html: string }) {
  return (
    <script
      type={typeof window === "undefined" ? "text/javascript" : "text/plain"}
      suppressHydrationWarning
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
