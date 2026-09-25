import re

_TOKEN = r"[\w.@/:=,\[\]-]+"
_ARG = rf"(?:{_TOKEN}|'{_TOKEN}')"  # 따옴표는 짝이 맞을 때만
_PKG = r"(?:@\w[\w.-]*/)?\w[\w.-]*(?:@[\w.-]+)?"  # npm 패키지명만. github:, URL, 경로 거부
_NPX = rf"npx(?: -y)? {_PKG}(?: {_ARG})*"
_UVX = rf"uvx {_ARG}(?: {_ARG})*"
_MCP_OPT = r"(?:-s|--scope|-e|--env|-t|--transport) [\w.=:/-]+"
PATTERNS = [re.compile(p) for p in (
    r"/plugin marketplace add [\w.-]+/[\w.-]+",
    r"/plugin install [\w.@-]+",
    rf"claude mcp add(?: {_MCP_OPT})* [\w.-]+ -- (?:{_NPX}|{_UVX})",
    _NPX,
    _UVX,
    r"pip install (?:[\w.\[\],=-]+|'[\w.\[\],=-]+')",
    r"npm install( -g)? [\w.@/-]+",
    r"git clone https://github\.com/[\w.-]+/[\w.-]+",
)]


def filter_commands(cmds: list[str]) -> list[str]:
    result: list[str] = []
    for cmd in (c.strip() for c in cmds):
        if cmd not in result and any(p.fullmatch(cmd) for p in PATTERNS):
            result.append(cmd)
    return result[:3]
