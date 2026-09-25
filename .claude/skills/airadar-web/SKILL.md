---
name: airadar-web
description: Airadar Next.js 웹 구현 규칙. web/ 폴더의 페이지(홈, /news, /tools, /trending), Neon DB 조회, 설치 명령 복사 버튼, UI 컴포넌트를 작성하거나 수정할 때 반드시 이 스킬을 사용한다.
---

# Airadar Web 규칙

스펙: `docs/superpowers/specs/2026-09-25-airadar-design.md` (§3 웹)

## 환경
- Next.js App Router + TypeScript + Tailwind. 패키지 추가는 최소화한다 (`@neondatabase/serverless` 외에는 필요한 이유가 있을 때만).
- 확인: `npm run build`, `npm run dev`

## 구조
| 위치 | 역할 |
|---|---|
| `web/lib/db.ts` | 모든 SQL 쿼리. 페이지 컴포넌트에 SQL을 직접 쓰지 않는다 |
| `web/lib/types.ts` | `db/schema.sql` 컬럼과 1:1로 맞춘 타입. 스키마가 바뀌면 여기부터 고친다 |
| `web/app/**/page.tsx` | 서버 컴포넌트. `export const revalidate = 3600` |
| `web/components/` | 클라이언트 상호작용이 필요한 것(복사 버튼, 필터)만 `"use client"` |

## 규칙
- 요약(`summary_ko`)이 NULL이면 원문 excerpt/description을 대신 보여 준다. 빈 칸을 만들지 않는다.
- 트렌드는 스냅샷이 7일 미만이면 "집계 중"을 표시한다.
- 설치 명령은 DB 값을 그대로 보여 주고 복사만 한다. 웹에서 명령을 만들거나 가공하지 않는다 (검증은 수집기가 맡는다).
- `DATABASE_URL`이 없으면 빈 상태를 렌더링하고 빌드는 통과해야 한다.
- UI 문구는 한국어로 쓴다.
