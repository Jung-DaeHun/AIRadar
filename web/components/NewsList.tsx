import type { NewsItem } from "@/lib/types";

export default function NewsList({ items }: { items: NewsItem[] }) {
  if (items.length === 0) return <p className="text-gray-500">아직 수집된 뉴스가 없습니다.</p>;
  return (
    <ul className="space-y-4">
      {items.map((n) => (
        <li key={n.id} className="rounded border p-4">
          <a href={n.url} target="_blank" rel="noreferrer" className="font-semibold hover:underline">
            {n.title}
          </a>
          <p className="mt-1 text-xs text-gray-500">
            {n.source}
            {n.published_at && ` · ${new Date(n.published_at).toLocaleDateString("ko-KR")}`}
          </p>
          {(n.summary_ko ?? n.excerpt) && (
            <p className="mt-2 whitespace-pre-line text-sm">{n.summary_ko ?? n.excerpt}</p>
          )}
        </li>
      ))}
    </ul>
  );
}
