---
name: airadar-collector
description: Airadar Python 수집기 구현 규칙. collector/ 코드, RSS·Hacker News·GeekNews·GitHub 수집, LLM 요약 Provider, 레포 점수 계산, 설치 명령 검증, db/schema.sql, GitHub Actions 크론 워크플로를 작성하거나 수정할 때 반드시 이 스킬을 사용한다.
---

# Airadar Collector 규칙

스펙: `docs/superpowers/specs/2026-09-25-airadar-design.md` (§2 데이터 모델, §3 흐름, §4 LLM, §5 오류 처리)

## 환경
- Python 3.12, 패키지 관리는 `uv` (`collector/pyproject.toml`). 의존성은 필요한 것만 추가한다: `httpx`, `feedparser`, `psycopg[binary]`, `pydantic`, `pytest`, 그리고 선택된 LLM SDK.
- 실행: `uv run python -m collector.run_news`, `uv run python -m collector.run_repos`

## 모듈 계약 (경계를 지키는 이유: 각 부분을 따로 테스트하고 교체하기 위해서)
| 모듈 | 계약 |
|---|---|
| `sources/*.py` | `fetch() -> list[dict]`. 네트워크만 다루고 DB나 LLM은 모른다. 반환 키는 `news_items`/`repos` 컬럼명과 같게 맞춘다 |
| `llm/base.py` | `Provider.summarize(text: str, kind: "news" \| "repo") -> dict`. `get_provider()`는 `LLM_PROVIDER` 환경 변수로 구현체를 고른다 |
| `scoring.py` | 순수 함수. DB 없이 숫자만 받아 점수를 반환한다 |
| `install_cmd.py` | `filter_commands(list[str]) -> list[str]`. 허용 패턴(스펙 §3-5)만 통과시킨다 |
| `db.py` | SQL은 이 파일에만 둔다. upsert 기준 키는 `url` / `full_name` |

## 규칙
- 소스 하나가 실패해도 나머지는 계속 진행한다. 실패는 로그로 남기고, 실행 종료 코드는 전체가 실패했을 때만 1로 한다.
- LLM 호출은 `LLM_MAX_CALLS`(기본 60)을 넘기지 않는다. 키가 없으면 요약 단계를 건너뛴다.
- LLM 출력은 pydantic 모델로 검증한다. 실패하면 `summary_ko`를 NULL로 둬서 다음 실행 때 재시도되게 한다.
- 비밀값은 환경 변수로만 읽는다. 코드와 fixture에 키를 넣지 않는다.

## 테스트
- 소스 파서: `collector/tests/fixtures/`에 저장한 실제 응답 샘플로 테스트한다. 테스트 중에는 네트워크를 쓰지 않는다.
- LLM: 가짜 Provider를 주입한다.
- `scoring`, `install_cmd`: 경계값(스냅샷 7일 미만, 위험 명령 `curl ... | sh`) 케이스를 포함한다.
