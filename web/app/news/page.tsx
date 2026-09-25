import FilterLinks from "@/components/FilterLinks";
import NewsList from "@/components/NewsList";
import { getNews, getNewsSources } from "@/lib/db";

export const revalidate = 3600;

export default async function NewsPage({ searchParams }: { searchParams: Promise<{ source?: string }> }) {
  const { source } = await searchParams;
  const [items, sources] = await Promise.all([getNews(source), getNewsSources()]);
  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold tracking-tight">AI 뉴스</h1>
      <FilterLinks base="/news" param="source" options={sources.map((s) => [s, s])} current={source} />
      <NewsList items={items} />
    </div>
  );
}
