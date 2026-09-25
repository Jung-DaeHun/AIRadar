export type NewsItem = {
  id: number;
  source: string;
  url: string;
  title: string;
  published_at: string | null;
  excerpt: string | null;
  lang: string;
  summary_ko: string | null;
};

export type Repo = {
  id: number;
  full_name: string;
  description: string | null;
  url: string;
  category: string | null;
  stars: number;
  weekly_star_delta: number | null;
  summary_ko: string | null;
  install_commands: string[];
};

export const CATEGORY_LABELS: Record<string, string> = {
  "claude-code-plugin": "Claude Code 플러그인",
  skill: "스킬",
  "mcp-server": "MCP 서버",
  "cursor-rules": "Cursor 규칙",
  "agent-framework": "에이전트 프레임워크",
  other: "기타",
};

export const TRENDING_EMPTY = "집계 중입니다. 스타 기록이 7일 이상 쌓이면 표시됩니다.";

export const NEW_REPOS_EMPTY = "최근 30일 내 생성된 레포가 아직 없습니다.";
