# Airadar 설계 스펙

## Context
빈 프로젝트 `Airadar`에서 AI 소식과 AI 코딩 도구 추천을 모아 보여 주는 웹 서비스를 새로 만든다.
- 용도: 본인 학습·포트폴리오(A). 완성도가 좋으면 일반 공개(B)로 확장.
- MVP 기능: ① 최신 AI 뉴스 ② GitHub AI 코딩 도구 확장 추천 ③ 한국어 요약/번역 ④ 급상승 레포 트렌드 ⑤ 원클릭 설치 명령 복사
- 추가 구현: ⑥ 주간 다이제스트(`/digest`, 매주 월요일 09:17 KST 생성), 마지막 수집 시각 표시
- 이후 단계 (이번 범위 아님): ⑦ 모델 릴리스 트래커 ⑨ 관심 태그·북마크(로그인)
- 비용은 0원에 가깝게: 무료 호스팅을 쓰고 LLM 호출만 소액 발생.

사용자와 합의한 결정
| 항목 | 결정 |
|---|---|
| 스택 | Python 수집 스크립트(GitHub Actions) + Neon Postgres + Next.js(Vercel). FastAPI는 ⑨ 단계에서 추가 |
| LLM | 운영자가 환경 변수 `LLM_PROVIDER`로 선택. 요약은 수집 시점에 미리 만들어 DB에 저장 |
| 뉴스 소스 | AI 기업 공식 블로그 RSS, Hacker News(AI 키워드), GeekNews |
| 추천 범위 | AI 코딩 도구 확장: Claude Code 플러그인·스킬, MCP 서버, Cursor 규칙, 에이전트 프레임워크 |
| 추천 방식 | 규칙으로 후보를 선별·채점하고, 상위 항목만 LLM이 분류·요약·설치 명령 추출 |

## 1. 아키텍처
```
GitHub Actions (cron)
  ├─ collect-news   (6시간마다)  ─┐
  └─ collect-repos  (매일 1회)   ─┼─▶ Neon Postgres ◀── Next.js (Vercel, ISR 1시간)
         └─ LLM 요약 (신규/변경 항목만) ─┘
```
모노레포 구조
```
Airadar/
├─ collector/            # Python 3.12, uv
│  ├─ sources/           # rss.py, hackernews.py, geeknews.py, github.py  (소스별 fetch → 공통 dict)
│  ├─ llm/               # base.py(Provider 인터페이스), claude.py, gemini.py, openai.py
│  ├─ scoring.py         # 레포 점수 계산
│  ├─ install_cmd.py     # 설치 명령 검증(허용 패턴)
│  ├─ db.py              # upsert/조회
│  ├─ run_news.py / run_repos.py   # 엔트리포인트
│  └─ tests/
├─ db/schema.sql
├─ web/                  # Next.js App Router + TypeScript + Tailwind
│  └─ app/  page.tsx(홈) · news/ · tools/ · trending/
└─ .github/workflows/  collect-news.yml · collect-repos.yml
```
각 단위는 하나의 역할만 맡는다. 소스 모듈은 fetch만 하고, LLM 모듈은 텍스트 → JSON만, db.py는 저장만 한다.

## 2. 데이터 모델 (db/schema.sql)
- `news_items`: id, source, url(UNIQUE), title, published_at, excerpt, lang, summary_ko(NULL 허용), created_at
- `repos`: id, full_name(UNIQUE), description, url, category, stars, pushed_at, topics[], readme_hash, summary_ko, install_commands(jsonb), score, updated_at
- `repo_star_snapshots`: repo_id, date, stars, PK(repo_id, date). ④ 주간 증가량 계산용

## 3. 데이터 흐름
**뉴스:** 소스별 fetch → URL 기준 중복 제거 → 신규만 insert → `summary_ko IS NULL`인 항목만 LLM으로 한국어 3줄 요약. GeekNews는 이미 한국어이므로 번역 없이 요약만 한다.

**레포:**
1. GitHub Search API로 토픽 검색(`claude-code`, `claude-code-plugin`, `mcp-server`, `model-context-protocol`, `cursor-rules`, `ai-agents` 등) → 후보 upsert
2. 당일 스타 스냅샷 저장
3. 점수 = 주간 스타 증가량(log) + 최근 push 가중치 + 총 스타(log). archived이거나 90일 이상 push가 없는 레포는 제외
4. 상위 N개(기본 50) 중 README 해시가 바뀐 것만 LLM 호출 → `{category, summary_ko, install_commands[]}` JSON
5. `install_cmd.py`가 허용 패턴만 통과시킨다(`/plugin marketplace add`, `/plugin install`, `claude mcp add`, `npx`, `uvx`, `pip install`, `npm install`, `git clone`). 나머지는 버린다. LLM이 만든 임의 셸 명령을 사용자에게 복사시키지 않기 위해서다.

**웹:** 서버 컴포넌트가 Neon을 직접 읽는다(`@neondatabase/serverless`). 페이지 구성: 홈(오늘의 뉴스 상위 + 급상승 5개), `/news`(소스 필터), `/tools`(카테고리 필터, 설치 명령 복사 버튼), `/trending`(주간 증가량 순). 스냅샷이 7일 미만이면 "집계 중" 표시.

## 4. LLM 제공자 추상화
`Provider.summarize(text, kind) -> dict` 인터페이스 하나만 둔다. `LLM_PROVIDER=claude|gemini|openai`, `LLM_API_KEY`, `LLM_MODEL`(선택)으로 설정한다. 기본값은 claude(Haiku 4.5). 출력은 JSON 스키마로 검증하고, 실패하면 NULL로 두어 다음 실행 때 재시도한다.

## 5. 오류 처리
- 소스끼리 격리: 한 소스가 실패해도 나머지는 계속 진행하고, 실패는 Actions 로그에 요약한다.
- LLM 실패 또는 키 없음: 요약 없이 저장하고, UI는 원문 excerpt/description을 보여 준다.
- GitHub rate limit: Actions의 `GITHUB_TOKEN`을 사용하고, Search API 분당 제한을 지키기 위해 요청 사이에 간격을 둔다.
- 1회 실행당 LLM 호출 상한(`LLM_MAX_CALLS`, 기본 60)을 둬서 비용 폭주를 막는다.

## 6. 설정 / 비밀값
GitHub Secrets: `DATABASE_URL`, `LLM_PROVIDER`, `LLM_API_KEY`, (`LLM_MODEL`). Vercel: `DATABASE_URL`(읽기 전용 역할 권장).

## 승인 후 진행 순서
1. 이 설계를 `docs/superpowers/specs/2026-09-25-airadar-design.md`로 저장한다. 현재 git 저장소가 아니므로 `git init` 후 커밋한다.
2. 스펙 자체 점검(모호함, 모순) 후 사용자 리뷰를 받는다.
3. 리뷰 승인 후 `superpowers:writing-plans`로 구현 계획을 작성한다. 코드 작성은 그 계획을 승인받은 뒤에 시작한다.

## 검증 방법 (구현 단계 기준)
- `collector`: pytest. 소스 파서는 저장된 응답 fixture로, 점수 계산과 설치 명령 검증기는 단위 테스트로, LLM은 가짜 Provider로 테스트한다.
- 로컬 E2E: Neon 브랜치 DB에 `uv run python -m collector.run_news` / `run_repos` 실행 → 행이 생성되는지 확인 → `web`에서 `npm run build && npm run dev`로 4개 페이지 확인.
- 배포 후: Actions `workflow_dispatch`로 수동 1회 실행 → Vercel 페이지에 반영되는지 확인.

## 범위 밖 (YAGNI)
로그인, 북마크, 모델 트래커, 논문 브리핑, 방문자 BYOK, FastAPI 서버.
