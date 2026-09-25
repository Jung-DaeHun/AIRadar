import CopyButton from "./CopyButton";
import { CATEGORY_LABELS, type Repo } from "@/lib/types";

function formatDelta(d: number) {
  return `${d >= 0 ? "+" : ""}${d.toLocaleString()}/주`;
}

export default function RepoCard({ repo }: { repo: Repo }) {
  return (
    <li className="rounded border p-4">
      <div className="flex items-baseline justify-between gap-2">
        <a href={repo.url} target="_blank" rel="noreferrer" className="font-semibold hover:underline">
          {repo.full_name}
        </a>
        <span className="shrink-0 text-xs text-gray-500">
          ★ {repo.stars.toLocaleString()}
          {repo.weekly_star_delta !== null && ` (${formatDelta(repo.weekly_star_delta)})`}
        </span>
      </div>
      {repo.category && (
        <span className="mt-1 inline-block rounded bg-gray-100 px-2 text-xs dark:bg-gray-800">
          {CATEGORY_LABELS[repo.category] ?? repo.category}
        </span>
      )}
      {(repo.summary_ko ?? repo.description) && (
        <p className="mt-2 whitespace-pre-line text-sm">{repo.summary_ko ?? repo.description}</p>
      )}
      {repo.install_commands.length > 0 && (
        <ul className="mt-3 space-y-1">
          {repo.install_commands.map((c) => (
            <li key={c} className="flex items-center gap-2">
              <code className="flex-1 overflow-x-auto rounded bg-gray-100 px-2 py-1 text-xs dark:bg-gray-800">{c}</code>
              <CopyButton text={c} />
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}
