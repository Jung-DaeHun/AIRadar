CREATE TABLE IF NOT EXISTS news_items (
  id           BIGSERIAL PRIMARY KEY,
  source       TEXT NOT NULL,
  url          TEXT NOT NULL UNIQUE,
  title        TEXT NOT NULL,
  published_at TIMESTAMPTZ,
  excerpt      TEXT,
  lang         TEXT NOT NULL DEFAULT 'en',
  summary_ko   TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS news_items_published_idx ON news_items (published_at DESC);

CREATE TABLE IF NOT EXISTS repos (
  id                BIGSERIAL PRIMARY KEY,
  full_name         TEXT NOT NULL UNIQUE,
  description       TEXT,
  url               TEXT NOT NULL,
  category          TEXT,
  stars             INTEGER NOT NULL DEFAULT 0,
  pushed_at         TIMESTAMPTZ,
  topics            TEXT[] NOT NULL DEFAULT '{}',
  readme_hash       TEXT,
  summary_ko        TEXT,
  install_commands  JSONB NOT NULL DEFAULT '[]',
  score             DOUBLE PRECISION NOT NULL DEFAULT 0,
  weekly_star_delta INTEGER,
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS repo_star_snapshots (
  repo_id BIGINT NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
  date    DATE NOT NULL,
  stars   INTEGER NOT NULL,
  PRIMARY KEY (repo_id, date)
);
