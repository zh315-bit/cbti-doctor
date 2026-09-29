"""Produce descriptive aggregates from a validator-approved completed review."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.v4_adjudication_contract import ROOT, TEMPLATE_PATH, aggregate_completed, read_jsonl


def main(argv=None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    records = [value for _, _, value in read_jsonl(args.input)]
    aggregate = aggregate_completed(records)
    output = args.output if args.output.is_absolute() else ROOT / args.output
    with output.open("x", encoding="utf-8") as stream:
        json.dump(aggregate, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")
    print(f"aggregation=WRITTEN cases={aggregate['n']}")


if __name__ == "__main__":
    main()
