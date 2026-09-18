"""Re-export backend test config for direct-script smoke runs."""
import sys
from pathlib import Path

_parent = str(Path(__file__).resolve().parents[1])
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from test_config import OWNER_ADMIN_PASSWORD  # noqa: E402

__all__ = ["OWNER_ADMIN_PASSWORD"]
