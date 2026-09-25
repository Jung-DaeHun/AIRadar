---
name: airadar-orchestrator
description: Airadar(AI 뉴스·AI 코딩 도구 추천 웹 서비스) 개발 하네스의 오케스트레이터. Airadar 구현 시작, 다음 태스크 진행, 수집기·웹 구현, 기능 추가 요청 시 반드시 이 스킬을 사용한다. 후속 작업: 다시 실행, 재실행, 이어서 진행, 업데이트, 수정, 보완, QA 실패 항목 고치기, 특정 태스크만 다시, 이전 결과 개선 요청에도 사용한다.
---

# Airadar Orchestrator

## 실행 모드: 서브 에이전트 (생성 → 검증 파이프라인)
Agent Teams가 꺼져 있어서 `Agent` 도구로 직접 호출한다. 모든 호출에 `model: "opus"`를 지정한다.

| 에이전트 | subagent_type | 스킬 | 출력 |
|---|---|---|---|
| collector-dev | collector-dev | airadar-collector | 코드 + `_workspace/{task}_collector-dev_report.md` |
| web-dev | web-dev | airadar-web | 코드 + `_workspace/{task}_web-dev_report.md` |
| qa-inspector | qa-inspector | airadar-qa | `_workspace/{task}_qa_report.md` |

기준 문서: 스펙 `docs/superpowers/specs/2026-09-25-airadar-design.md`, 계획 `docs/superpowers/plans/2026-09-25-airadar-plan.md`

## Phase 0: 컨텍스트 확인
1. 계획 파일이 없으면 → Phase 1
2. `_workspace/progress.md`가 있으면 → 완료된 태스크를 건너뛰고 Phase 2의 다음 태스크부터 진행
3. 사용자가 특정 태스크 재작업을 요청하면 → 그 태스크만 Phase 2로 다시 실행 (이전 보고서 경로를 프롬프트에 포함)

## Phase 1: 구현 계획 작성
`superpowers:writing-plans` 스킬로 스펙을 태스크 목록으로 나눈다. 각 태스크에는 담당(collector-dev / web-dev), 검증 방법을 적는다. 권장 순서:
1. 스키마 + 수집기 골격 + LLM Provider → 2. 뉴스 소스 → 3. 레포 수집·점수·설치 명령 검증 → 4. 웹 → 5. Actions 워크플로·배포 문서
계획은 사용자 승인을 받은 뒤 Phase 2로 넘어간다.

## Phase 2: 태스크 실행 루프
태스크마다:
1. 담당 개발 에이전트 호출 (태스크 번호, 계획 경로, 이전 QA 보고서가 있으면 그 경로 전달)
2. qa-inspector 호출
3. `FAIL`이면 QA 보고서를 담당 에이전트에게 전달해 재작업 → 다시 QA. **최대 2회**까지만 반복하고, 그래도 실패하면 멈추고 사용자에게 보고한다
4. `PASS`면 `_workspace/progress.md`에 한 줄 기록 (`- [x] T{n} 제목`)

**병렬 실행:** 스키마 태스크가 끝난 뒤에는 서로 독립적인 수집기 태스크와 웹 태스크를 `run_in_background: true`로 동시에 돌릴 수 있다. 스키마를 바꾸는 태스크는 단독으로 실행한다.

## Phase 3: 보고
사용자에게 **짧게** 보고한다: 완료 태스크, 실패/질문 항목, 다음 할 일을 각각 1~3줄로. 코드 전문이나 긴 로그는 붙이지 않는다.
CLAUDE.md에는 하네스 구성이 바뀌었을 때만 변경 이력 한 줄을 추가한다. 태스크 진행 내역은 `progress.md`에만 적는다.

## 에러 핸들링
| 상황 | 대응 |
|---|---|
| 에이전트 실패/중단 | 1회 재호출. 다시 실패하면 해당 태스크를 보류로 표시하고 사용자에게 보고 |
| 보고서의 "질문" 항목 | 추측하지 말고 사용자에게 묻는다 |
| 스키마 변경 발생 | 다음 web 태스크 프롬프트에 변경 내용을 명시한다 |

## 테스트 시나리오
- **정상:** "Airadar 구현 시작해줘" → 계획 작성·승인 → T1 collector-dev → QA PASS → progress 기록 → T2…
- **에러:** T3 QA에서 `db.py`의 컬럼명 불일치로 FAIL → 보고서를 collector-dev에 전달해 수정 → 재QA PASS. 2회 연속 FAIL이면 중단하고 보고한다.
