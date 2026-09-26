import { neon } from "@neondatabase/serverless";
import type { Digest, NewsItem, Repo } from "./types";

const sql = process.env.DATABASE_URL ? neon(process.env.DATABASE_URL) : null;

// 새 테이블은 다음 수집 실행 때 생성되므로, 아직 없으면(42P01) 빈 값으로 처리한다.
function orIfNoTable<T>(fallback: T) {
  return (e: unknown): T => {
    if ((e as { code?: string }).code === "42P01") return fallback;
    throw e;
  };
}

export async function getNews(source?: string, limit = 50): Promise<NewsItem[]> {
  if (!sql) return [];
  const s = source || null;
  return (await sql`
    SELECT id::int, source, url, title, published_at::text, excerpt, lang, summary_ko
    FROM news_items
    WHERE ${s}::text IS NULL OR source = ${s}
    ORDER BY published_at DESC NULLS LAST
    LIMIT ${limit}`) as NewsItem[];
}

export async function getNewsSources(): Promise<string[]> {
  if (!sql) return [];
  const rows = await sql`SELECT DISTINCT source FROM news_items ORDER BY source`;
  return rows.map((r) => r.source as string);
}

export async function getTools(category?: string, limit = 50): Promise<Repo[]> {
  if (!sql) return [];
  const c = category || null;
  return (await sql`
    SELECT id::int, full_name, description, url, category, stars, weekly_star_delta, summary_ko, install_commands
    FROM repos
    WHERE summary_ko IS NOT NULL
      AND pushed_at >= now() - interval '90 days'
      AND updated_at >= now() - interval '2 days'
      AND (${c}::text IS NULL OR category = ${c})
    ORDER BY score DESC
    LIMIT ${limit}`) as Repo[];
}

export async function getTrending(limit = 30): Promise<Repo[]> {
  if (!sql) return [];
  return (await sql`
    SELECT id::int, full_name, description, url, category, stars, weekly_star_delta, summary_ko, install_commands
    FROM repos
    WHERE weekly_star_delta IS NOT NULL AND pushed_at >= now() - interval '90 days'
      AND updated_at >= now() - interval '2 days'
    ORDER BY weekly_star_delta DESC
    LIMIT ${limit}`) as Repo[];
}

export async function getNewRepos(limit = 20): Promise<Repo[]> {
  if (!sql) return [];
  return (await sql`
    SELECT id::int, full_name, description, url, category, stars, weekly_star_delta, summary_ko, install_commands
    FROM repos
    WHERE created_at >= now() - interval '30 days'
      AND updated_at >= now() - interval '2 days'
    ORDER BY stars DESC
    LIMIT ${limit}`) as Repo[];
}

export async function getLastRuns(): Promise<{ news?: string; repos?: string }> {
  if (!sql) return {};
  const rows = await sql`SELECT name, finished_at::text FROM collector_runs`.catch(orIfNoTable([]));
  return Object.fromEntries(rows.map((r) => [r.name as string, r.finished_at as string]));
}

export async function getDigests(limit = 8): Promise<Digest[]> {
  if (!sql) return [];
  return (await sql`
    SELECT id::int, week_start::text, title_ko, body_ko, created_at::text
    FROM digests
    ORDER BY week_start DESC
    LIMIT ${limit}`.catch(orIfNoTable([]))) as Digest[];
}
