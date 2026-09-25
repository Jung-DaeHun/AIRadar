"""Stop: 응답을 마치기 전에 collector 테스트를 돌리고, 실패하면 계속 고치게 한다."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> None:
    sys.stderr.reconfigure(encoding="utf-8")
    data = json.loads(sys.stdin.buffer.read().decode("utf-8") or "{}")
    if data.get("stop_hook_active"):  # 이미 한 번 막았으면 무한 반복을 피한다
        return
    collector = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")) / "collector"
    if not (collector / "pyproject.toml").exists() or not shutil.which("uv"):
        return
    r = subprocess.run(["uv", "run", "pytest", "-q", "-x"], cwd=collector,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode not in (0, 5):  # 5 = 수집된 테스트 없음
        print(f"collector 테스트가 실패했습니다. 고친 뒤 마무리하세요.\n{r.stdout[-2000:]}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
