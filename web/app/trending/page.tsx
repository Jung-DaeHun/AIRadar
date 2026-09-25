import RepoList from "@/components/RepoList";
import { getTrending } from "@/lib/db";
import { TRENDING_EMPTY } from "@/lib/types";

export const revalidate = 3600;

export default async function TrendingPage() {
  const repos = await getTrending();
  return (
    <div>
      <h1 className="mb-4 text-2xl font-bold">이번 주 급상승 레포</h1>
      <RepoList repos={repos} empty={TRENDING_EMPTY} />
    </div>
  );
}
