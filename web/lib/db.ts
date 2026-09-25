import { neon } from "@neondatabase/serverless";
import type { NewsItem, Repo } from "./types";

const sql = process.env.DATABASE_URL ? neon(process.env.DATABASE_URL) : null;

export async function getNews(source?: string, limit = 50): Promise<NewsItem[]> {
  if (!sql) return [];
  const s = source ?? null;
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
  const c = category ?? null;
  return (await sql`
    SELECT id::int, full_name, description, url, category, stars, weekly_star_delta, summary_ko, install_commands
    FROM repos
    WHERE summary_ko IS NOT NULL
      AND pushed_at >= now() - interval '90 days'
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
    ORDER BY weekly_star_delta DESC
    LIMIT ${limit}`) as Repo[];
}
