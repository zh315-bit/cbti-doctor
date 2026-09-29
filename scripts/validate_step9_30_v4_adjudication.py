"""Fail-closed validator for V4 frozen-rubric adjudication JSONL."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.v4_adjudication_contract import TEMPLATE_PATH, read_jsonl, validate_records


def main(argv=None) -> None:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--template", action="store_true")
    modes.add_argument("--completed", action="store_true")
    parser.add_argument("--input", type=Path, default=TEMPLATE_PATH)
    args = parser.parse_args(argv)
    records = [value for _, _, value in read_jsonl(args.input)]
    mode = "completed" if args.completed else "template"
    validate_records(records, mode)
    print(f"validation=PASS mode={mode} cases={len(records)}")


if __name__ == "__main__":
    main()
