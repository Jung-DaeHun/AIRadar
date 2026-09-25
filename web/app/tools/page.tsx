import FilterLinks from "@/components/FilterLinks";
import RepoList from "@/components/RepoList";
import { getTools } from "@/lib/db";
import { CATEGORY_LABELS } from "@/lib/types";

export const revalidate = 3600;

export default async function ToolsPage({ searchParams }: { searchParams: Promise<{ category?: string }> }) {
  const { category } = await searchParams;
  const repos = await getTools(category);
  return (
    <div>
      <h1 className="mb-4 text-2xl font-bold">AI 코딩 도구 추천</h1>
      <FilterLinks base="/tools" param="category" options={Object.entries(CATEGORY_LABELS)} current={category} />
      <RepoList repos={repos} empty="아직 추천할 도구가 없습니다." />
    </div>
  );
}
