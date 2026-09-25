import CopyButton from "./CopyButton";
import { CATEGORY_LABELS, type Repo } from "@/lib/types";

function formatDelta(d: number) {
  return `${d >= 0 ? "+" : ""}${d.toLocaleString()}/주`;
}

export default function RepoCard({ repo }: { repo: Repo }) {
  return (
    <li className="py-6 first:pt-0">
      <div className="flex items-baseline justify-between gap-3">
        <div className="min-w-0">
          <a href={repo.url} target="_blank" rel="noreferrer" className="break-all text-lg font-bold hover:text-accent">
            {repo.full_name}
          </a>
          {repo.category && (
            <span className="ml-2 text-xs text-muted">{CATEGORY_LABELS[repo.category] ?? repo.category}</span>
          )}
        </div>
        <span className="shrink-0 text-sm text-muted">
          ★ {repo.stars.toLocaleString()}
          {repo.weekly_star_delta !== null && (
            <span className="ml-2 font-semibold text-accent">{formatDelta(repo.weekly_star_delta)}</span>
          )}
        </span>
      </div>
      {(repo.summary_ko ?? repo.description) && (
        <p className="mt-2 whitespace-pre-line text-[15px] text-foreground/80">{repo.summary_ko ?? repo.description}</p>
      )}
      {repo.install_commands.length > 0 && (
        <ul className="mt-3 space-y-2">
          {repo.install_commands.map((c) => (
            <li key={c} className="flex items-center gap-2 rounded-md bg-code py-1 pl-3 pr-1">
              <code className="flex-1 overflow-x-auto whitespace-nowrap font-mono text-[13px]">{c}</code>
              <CopyButton text={c} />
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}
