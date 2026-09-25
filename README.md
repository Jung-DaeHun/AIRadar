# Airadar

AI 뉴스와 AI 코딩 도구(플러그인·스킬·MCP 서버) 추천을 한국어 요약과 함께 보여 주는 웹 서비스.

## 구조
GitHub Actions(수집·요약) → Neon Postgres → Next.js(Vercel)

## 로컬 실행
```bash
cd collector && uv sync --all-extras && uv run pytest
# 저장소 루트에서
DATABASE_URL=... LLM_API_KEY=... uv run --project collector python -m collector.run_news
DATABASE_URL=... uv run --project collector python -m collector.run_repos
cd web && npm install && DATABASE_URL=... npm run dev
```
PowerShell에서는 `$env:DATABASE_URL="..."`로 먼저 설정한다.

## 환경 변수
| 이름 | 설명 |
|---|---|
| `DATABASE_URL` | Neon 연결 문자열 |
| `LLM_PROVIDER` | `claude`(기본) / `gemini` / `openai` |
| `LLM_API_KEY` | 선택한 제공자의 키. 없으면 요약을 건너뛴다 |
| `LLM_MODEL` | 모델 ID. gemini/openai는 필수 |
| `LLM_MAX_CALLS` | 실행당 LLM 호출 상한 (기본 60) |
| `GITHUB_TOKEN` | GitHub API 토큰(선택). 없으면 Search API 호출 간격을 늘린다. Actions에서는 자동 제공된다 |

## 배포
1. Neon에서 프로젝트를 만들고 연결 문자열을 복사한다 (테이블은 수집기가 처음 실행될 때 자동 생성된다).
2. GitHub 저장소 Settings → Secrets → Actions에 `DATABASE_URL`, `LLM_API_KEY`(필요하면 `LLM_PROVIDER`, `LLM_MODEL`)를 등록한다. `GITHUB_TOKEN`은 Actions가 자동으로 넣어 주므로 등록하지 않는다.
3. Actions 탭에서 `collect-news`, `collect-repos`를 `Run workflow`로 한 번 실행한다.
4. Vercel에서 저장소를 가져오고 Root Directory를 `web`으로, 환경 변수 `DATABASE_URL`을 설정해 배포한다.
5. 급상승 트렌드는 스타 기록이 7일 이상 쌓인 뒤부터 표시된다.

### 주의
- **Vercel 빌드 환경에도 `DATABASE_URL`이 필요하다.** 빌드 시 값이 없으면 `/`, `/trending`이 빈 페이지로 미리 생성되어 첫 재검증(1시간)까지 빈 화면이 보인다. Vercel 환경 변수를 Production·Preview 모두에 설정하고 배포한다.
- **웹은 PowerShell 등 일반 환경에서 빌드한다.** Windows의 Git Bash에서 `npm run build`를 실행하면 Turbopack이 `0xc0000142` 오류로 실패할 수 있다.
