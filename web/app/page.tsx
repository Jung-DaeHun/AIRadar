import Link from "next/link";
import NewsList from "@/components/NewsList";
import RepoList from "@/components/RepoList";
import { getNews, getTrending } from "@/lib/db";
import { TRENDING_EMPTY } from "@/lib/types";

export const revalidate = 3600;

export default async function Home() {
  const [news, trending] = await Promise.all([getNews(undefined, 5), getTrending(5)]);
  return (
    <div className="space-y-10">
      <section>
        <h2 className="mb-3 text-lg font-bold">
          최신 AI 뉴스 <Link href="/news" className="ml-2 text-sm font-normal text-blue-600">더 보기</Link>
        </h2>
        <NewsList items={news} />
      </section>
      <section>
        <h2 className="mb-3 text-lg font-bold">
          이번 주 급상승 <Link href="/trending" className="ml-2 text-sm font-normal text-blue-600">더 보기</Link>
        </h2>
        <RepoList repos={trending} empty={TRENDING_EMPTY} />
      </section>
    </div>
  );
}
