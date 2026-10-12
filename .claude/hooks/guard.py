#!/usr/bin/env python3
"""PreToolUse guard for Bash: blocks destructive git operations.
Exit code 2 = block (message goes back to Claude)."""
import json
import re
import sys

cmd = (json.load(sys.stdin).get("tool_input") or {}).get("command", "")

DESTRUCTIVE = re.compile(r"\bgit\s+(push\s+.*(--force\b|-f\b|--mirror\b)|reset\s+--hard|clean\s+-[a-z]*f)")

if DESTRUCTIVE.search(cmd):
    print("BLOCKED: destructive git command (force push / reset --hard / clean -f). Ask the user first.", file=sys.stderr)
    sys.exit(2)
sys.exit(0)
