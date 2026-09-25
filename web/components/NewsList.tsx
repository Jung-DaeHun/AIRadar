import type { NewsItem } from "@/lib/types";
import { formatNewsTime } from "@/lib/time";

export default function NewsList({ items }: { items: NewsItem[] }) {
  if (items.length === 0) return <p className="py-12 text-center text-sm text-muted">아직 수집된 뉴스가 없습니다.</p>;
  return (
    <ul className="divide-y divide-line">
      {items.map((n) => {
        const time = n.published_at && formatNewsTime(n.published_at, n.source);
        return (
          <li key={n.id} className="py-6 first:pt-0">
            <p className="text-xs text-muted">
              {n.source}
              {time && ` · ${time}`}
            </p>
            <a
              href={n.url}
              target="_blank"
              rel="noreferrer"
              className="mt-1 block text-lg font-bold leading-snug hover:text-accent"
            >
              {n.title}
            </a>
            {(n.summary_ko ?? n.excerpt) && (
              <p className="mt-2 line-clamp-3 whitespace-pre-line text-[15px] text-foreground/80">
                {n.summary_ko ?? n.excerpt}
              </p>
            )}
          </li>
        );
      })}
    </ul>
  );
}
