"""TDD Guard — PreToolUse[Edit|Write]
collector/ 구현 파일(.py)을 수정하려면 그 모듈을 참조하는 테스트가 collector/tests/에 먼저 있어야 한다.
"""
import json
import re
import sys
from pathlib import Path


def deny(reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}))
    sys.exit(0)


def main() -> None:
    data = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    path = Path(data.get("tool_input", {}).get("file_path", ""))

    # collector/ 밖의 파일, .py가 아닌 파일, 테스트 파일, __init__.py는 통과
    collector = next((p for p in path.parents if p.name == "collector"), None)
    if collector is None or path.suffix != ".py":
        return
    if "tests" in path.parts or path.name == "__init__.py":
        return

    module = path.stem
    tests_dir = collector / "tests"
    pattern = re.compile(rf"\b{re.escape(module)}\b")
    for test in tests_dir.glob("test_*.py"):
        if test.stem == f"test_{module}" or pattern.search(test.read_text(encoding="utf-8")):
            return

    deny(f"TDD GUARD: '{module}' 모듈을 참조하는 테스트가 collector/tests/에 없습니다. "
         f"구현 전에 테스트를 먼저 작성하세요 (예: collector/tests/test_{module}.py).")


if __name__ == "__main__":
    main()
