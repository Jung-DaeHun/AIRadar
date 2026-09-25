import RepoList from "@/components/RepoList";
import { getNewRepos, getTrending } from "@/lib/db";
import { NEW_REPOS_EMPTY, TRENDING_EMPTY } from "@/lib/types";

export const revalidate = 3600;

export default async function TrendingPage() {
  const [repos, newRepos] = await Promise.all([getTrending(), getNewRepos()]);
  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold tracking-tight">이번 주 급상승 레포</h1>
      <RepoList repos={repos} empty={TRENDING_EMPTY} />
      <h2 className="mb-6 mt-14 text-xl font-bold tracking-tight">이번 달 신규 레포</h2>
      <RepoList repos={newRepos} empty={NEW_REPOS_EMPTY} />
    </div>
  );
}
