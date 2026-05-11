from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"

for path in (
    PROJECT_ROOT,
    SCRIPTS_ROOT / "analysis",
    SCRIPTS_ROOT / "tep",
    SCRIPTS_ROOT / "visualization",
    SCRIPTS_ROOT / "robustness",
):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
