import Link from "next/link";
import RepoList from "@/components/RepoList";
import { getDigests, getTrending } from "@/lib/db";
import { TRENDING_EMPTY } from "@/lib/types";

export const revalidate = 3600;

function SectionHeader({ title, href }: { title: string; href: string }) {
  return (
    <div className="mb-4 flex items-baseline justify-between border-b border-line pb-2">
      <h2 className="text-sm font-bold">{title}</h2>
      <Link href={href} className="text-sm text-muted hover:text-accent">더 보기 →</Link>
    </div>
  );
}

export default async function Home() {
  const [[digest], trending] = await Promise.all([getDigests(1), getTrending(5)]);
  return (
    <div className="space-y-14">
      <section>
        <SectionHeader title="주간 다이제스트" href="/digest" />
        {!digest ? (
          <p className="py-12 text-center text-sm text-muted">첫 다이제스트는 월요일 오전에 발행됩니다.</p>
        ) : (
          <article>
            <h3 className="text-lg font-bold leading-snug">{digest.title_ko}</h3>
            <p className="mt-3 whitespace-pre-line text-[15px] leading-relaxed text-foreground/80">{digest.body_ko}</p>
          </article>
        )}
      </section>
      <section>
        <SectionHeader title="이번 주 급상승" href="/trending" />
        <RepoList repos={trending} empty={TRENDING_EMPTY} />
      </section>
    </div>
  );
}
