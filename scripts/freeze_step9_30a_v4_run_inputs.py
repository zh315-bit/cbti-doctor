"""Freeze the already completed V4 attempt inputs; never executes a case."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.v4_adjudication_contract import FREEZE_PATH, create_run_input_freeze


def main() -> None:
    value = create_run_input_freeze()
    with FREEZE_PATH.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")
    print(f"frozen={FREEZE_PATH}")


if __name__ == "__main__":
    main()
