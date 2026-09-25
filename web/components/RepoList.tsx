import RepoCard from "./RepoCard";
import type { Repo } from "@/lib/types";

export default function RepoList({ repos, empty }: { repos: Repo[]; empty: string }) {
  if (repos.length === 0) return <p className="py-12 text-center text-sm text-muted">{empty}</p>;
  return (
    <ul className="divide-y divide-line">
      {repos.map((r) => (
        <RepoCard key={r.id} repo={r} />
      ))}
    </ul>
  );
}
