"""Generate one unset reviewer template row per frozen V4 case."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.v4_adjudication_contract import TEMPLATE_PATH, generate_template


def main() -> None:
    records = generate_template()
    with TEMPLATE_PATH.open("x", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"template_rows={len(records)}")


if __name__ == "__main__":
    main()
