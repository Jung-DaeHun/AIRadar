---
name: airadar-qa
description: Airadar 구현 태스크의 QA 체크리스트. 스키마·수집기·웹 사이의 경계면 정합성 교차 검증, pytest와 next build 실행, 태스크 완료 검수가 필요할 때 반드시 이 스킬을 사용한다.
---

# Airadar QA 체크리스트

버그는 대부분 모듈 안이 아니라 **모듈 사이**에서 생긴다. 양쪽 파일을 동시에 열어 비교한다.

## 1. 경계면 교차 비교 (해당 태스크가 건드린 부분만)
| 경계 | 비교 방법 |
|---|---|
| `db/schema.sql` ↔ `collector/db.py` | INSERT/UPSERT 컬럼명·타입·NOT NULL이 스키마와 일치하는가 |
| `collector/sources/*` ↔ `db.py` | `fetch()` 반환 dict의 키가 `db.py`가 기대하는 키와 같은가 |
| `db/schema.sql` ↔ `web/lib/types.ts` | 컬럼명, NULL 허용 여부(`string \| null`)가 일치하는가 |
| `web/lib/db.ts` ↔ 페이지 | 쿼리가 반환하는 필드를 페이지가 그대로 쓰는가. jsonb(`install_commands`)의 구조가 맞는가 |
| LLM 출력 모델 ↔ DB | pydantic 필드와 저장 컬럼이 맞는가 |

## 2. 실행 검증
- 수집기 변경: `cd collector && uv run pytest`
- 웹 변경: `cd web && npm run build`
- 실행할 수 없으면 이유를 적고 정적 검증만 한다.

## 3. 스펙 준수
- 범위 밖 기능(로그인, 북마크 등)이 추가되지 않았는가
- 설치 명령 허용 패턴 우회 가능성, 비밀값 하드코딩이 없는가

## 보고 형식 (`_workspace/{task}_qa_report.md`)
```
PASS | FAIL
- [심각도] 파일:줄 — 문제 한 줄 / 재현 방법
```
