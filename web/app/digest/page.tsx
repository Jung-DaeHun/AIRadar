import { getDigests } from "@/lib/db";

export const revalidate = 3600;

// week_start("2026-09-21")를 "9월 21일 주간"으로 표시한다.
function weekLabel(weekStart: string) {
  const [, m, d] = weekStart.split("-").map(Number);
  return `${m}월 ${d}일 주간`;
}

export default async function DigestPage() {
  const [latest, ...past] = await getDigests();
  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold tracking-tight">주간 다이제스트</h1>
      {!latest ? (
        <p className="py-12 text-center text-sm text-muted">첫 다이제스트는 월요일 오전에 발행됩니다.</p>
      ) : (
        <article>
          <p className="text-xs text-muted">{weekLabel(latest.week_start)}</p>
          <h2 className="mt-1 text-xl font-bold leading-snug">{latest.title_ko}</h2>
          <p className="mt-4 whitespace-pre-line text-[15px] leading-relaxed text-foreground/80">{latest.body_ko}</p>
        </article>
      )}
      {past.length > 0 && (
        <>
          <h2 className="mb-6 mt-14 text-xl font-bold tracking-tight">지난 다이제스트</h2>
          <ul className="divide-y divide-line">
            {past.map((d) => (
              <li key={d.id} className="py-4 first:pt-0">
                <p className="text-xs text-muted">{weekLabel(d.week_start)}</p>
                <p className="mt-1 font-semibold">{d.title_ko}</p>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
