// 뉴스 시간 표시: 한국 시간 + 소스별 현지 시간. 서버 시간대와 무관하게 timeZone을 명시한다.
const SOURCE_ZONES: Record<string, [string, string]> = {
  openai: ["America/Los_Angeles", "PT"],
  "google-ai": ["America/Los_Angeles", "PT"],
  hackernews: ["America/Los_Angeles", "PT"],
  deepmind: ["Europe/London", "UK"],
  huggingface: ["America/New_York", "ET"],
};

function format(date: Date, timeZone: string, label: string) {
  const parts = new Intl.DateTimeFormat("ko-KR", {
    timeZone,
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(date);
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? "";
  return `${get("month")}월 ${get("day")}일 ${get("hour")}:${get("minute")} ${label}`;
}

// Postgres timestamptz::text("2026-09-25 05:30:00+00")를 ISO 형식으로 바꿔 파싱한다.
function parse(value: string) {
  return new Date(value.replace(" ", "T").replace(/([+-]\d{2})$/, "$1:00"));
}

export function formatNewsTime(publishedAt: string, source: string): string | null {
  const date = parse(publishedAt);
  if (Number.isNaN(date.getTime())) return null;
  const kst = format(date, "Asia/Seoul", "KST");
  const local = SOURCE_ZONES[source];
  return local ? `${kst} · ${format(date, local[0], local[1])}` : kst;
}

export function formatKst(value: string): string | null {
  const date = parse(value);
  return Number.isNaN(date.getTime()) ? null : format(date, "Asia/Seoul", "KST");
}
