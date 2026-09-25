import RepoCard from "./RepoCard";
import type { Repo } from "@/lib/types";

export default function RepoList({ repos, empty }: { repos: Repo[]; empty: string }) {
  if (repos.length === 0) return <p className="text-gray-500">{empty}</p>;
  return (
    <ul className="space-y-4">
      {repos.map((r) => (
        <RepoCard key={r.id} repo={r} />
      ))}
    </ul>
  );
}
