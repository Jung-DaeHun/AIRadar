"""PreToolUse[Bash]: 되돌리기 어려운 위험 명령을 실행 전에 차단한다."""
import json
import re
import sys

DANGEROUS = {
    "rm -rf": r"\brm\s+(-\w*r\w*f|-\w*f\w*r|-r\s+-f|-f\s+-r|--recursive\s+--force|--force\s+--recursive)",
    "git push --force": r"\bgit\s+push\b.*\s(--force(?!-with-lease)\b|-f\b)",
    "git reset --hard": r"\bgit\s+reset\s+--hard\b",
    "git clean -f": r"\bgit\s+clean\s+-\w*f",
    "DROP TABLE/DATABASE": r"\bDROP\s+(TABLE|DATABASE|SCHEMA)\b",
}


def main() -> None:
    sys.stderr.reconfigure(encoding="utf-8")
    data = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    command = data.get("tool_input", {}).get("command", "")
    for label, pattern in DANGEROUS.items():
        if re.search(pattern, command, re.IGNORECASE):
            print(f"BLOCKED: 위험한 명령어가 감지되었습니다 ({label}). 필요하면 사용자가 직접 실행하세요.",
                  file=sys.stderr)
            sys.exit(2)


if __name__ == "__main__":
    main()
