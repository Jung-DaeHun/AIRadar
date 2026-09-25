import re

_ARG = r"[\w.@/:=,'\[\]-]+"
PATTERNS = [re.compile(p) for p in (
    r"/plugin marketplace add [\w.-]+/[\w.-]+",
    r"/plugin install [\w.@-]+",
    rf"claude mcp add( {_ARG})+",
    rf"npx( -y)? {_ARG}( {_ARG})*",
    rf"uvx {_ARG}( {_ARG})*",
    r"pip install [\w.'\[\],=-]+",
    r"npm install( -g)? [\w.@/-]+",
    r"git clone https://github\.com/[\w.-]+/[\w.-]+",
)]


def filter_commands(cmds: list[str]) -> list[str]:
    result: list[str] = []
    for cmd in (c.strip() for c in cmds):
        if cmd not in result and any(p.fullmatch(cmd) for p in PATTERNS):
            result.append(cmd)
    return result[:3]
