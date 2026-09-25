import Link from "next/link";
import NewsList from "@/components/NewsList";
import RepoList from "@/components/RepoList";
import { getNews, getTrending } from "@/lib/db";
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
  const [news, trending] = await Promise.all([getNews(undefined, 5), getTrending(5)]);
  return (
    <div className="space-y-14">
      <section>
        <SectionHeader title="최신 AI 뉴스" href="/news" />
        <NewsList items={news} />
      </section>
      <section>
        <SectionHeader title="이번 주 급상승" href="/trending" />
        <RepoList repos={trending} empty={TRENDING_EMPTY} />
      </section>
    </div>
  );
}
