#!/usr/bin/env python3
"""PreToolUse guard for Bash: blocks writes to the read-only repo DanielIgna/propmanage-online
and destructive git operations. Exit code 2 = block (message goes back to Claude)."""
import json
import re
import sys

cmd = (json.load(sys.stdin).get("tool_input") or {}).get("command", "")

READ_ONLY_REPO = re.compile(r"DanielIgna/propmanage-online(?![\w-])")
WRITE_OPS = re.compile(
    r"\bgit\s+(push|remote\s+(add|set-url))\b"
    r"|\bgh\s+(pr\s+(create|merge|close|edit|comment|review)|repo\s+(edit|delete|rename|archive|sync)"
    r"|release\s+(create|delete|edit)|issue\s+(create|close|edit|comment)|workflow\s+(run|enable|disable)|secret|variable)\b"
    r"|\bgh\s+api\b.*(-X|--method)\s*(POST|PUT|PATCH|DELETE)"
)
DESTRUCTIVE = re.compile(r"\bgit\s+(push\s+.*(--force\b|-f\b|--mirror\b)|reset\s+--hard|clean\s+-[a-z]*f)")

if READ_ONLY_REPO.search(cmd) and WRITE_OPS.search(cmd):
    print("BLOCKED: DanielIgna/propmanage-online is read-only (CLAUDE.md). Write only to propmanage-app.", file=sys.stderr)
    sys.exit(2)
if DESTRUCTIVE.search(cmd):
    print("BLOCKED: destructive git command (force push / reset --hard / clean -f). Ask the user first.", file=sys.stderr)
    sys.exit(2)
sys.exit(0)
