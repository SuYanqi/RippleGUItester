#!/usr/bin/env python
"""Reproduce RQ3 missed ground-truth bug analysis.

This script reproduces the analysis in Section 4.4.1:
"Analysis of Missed Ground-Truth Bugs".

Input:
    output/Firefox/missed_gui_bug_reasons.json

Run:
    python -m scripts.evaluation.analyze_missed_ground_truth_bugs
"""

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "output"
APP = "Firefox"


RQ3_MISSED_REASON_STRUCTURE = {
    "Limitations in test scenario generation coverage": [
        "Hard-to-predict trigger steps",
        "Strict trigger steps",
    ],
    "Incomplete test scenario execution": [
        "Reaching the maximum execution budget",
        "Incorrect execution",
    ],
}


RAW_REASON_TO_SUBCATEGORY = {
    # 4.4.1: Limitations in test scenario generation coverage
    "unexpected trigger condition -> test scenario generation not covered":
        "Hard-to-predict trigger steps",

    "complex trigger condition -> test scenario generation not covered":
        "Strict trigger steps",

    # 4.4.1: Incomplete test scenario execution
    "reach maximum execution times -> incomplete test scenario execution":
        "Reaching the maximum execution budget",

    "Execution element location error -> incomplete test scenario execution":
        "Incorrect execution",

    "trigger path execution error":
        "Incorrect execution",

    "false execution path -> stuck -> reach maximum execution times -> incomplete test scenario execution":
        "Incorrect execution",

    "build error -> incomplete test scenario execution":
        "Incorrect execution",

    "UI interaction Error Implemantation (drag need two coordinates but in implementation only) -> incomplete test scenario execution":
        "Incorrect execution",

    "generated test file has random name -> replay failure -> detector missing the comparison change":
        "Incorrect execution",
}


SUBCATEGORY_TO_CATEGORY = {
    subcategory: category
    for category, subcategories in RQ3_MISSED_REASON_STRUCTURE.items()
    for subcategory in subcategories
}


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON file: {path}") from exc


def normalize_reason(reason: str) -> str:
    return reason.strip() if isinstance(reason, str) else str(reason)


def load_missed_bug_labels() -> list:
    input_file = OUTPUT_DIR / APP / "missed_gui_bug_reasons.json"
    if not input_file.exists():
        raise FileNotFoundError(f"Missing missed-bug reason file: {input_file}")
    return load_json(input_file)


def collect_missed_bug_distribution():
    data = load_missed_bug_labels()

    category_counter = Counter()
    subcategory_counter = Counter()
    raw_reason_counter = Counter()
    grouped_raw_reasons = defaultdict(Counter)
    pr_counter = Counter()
    unmapped_reasons = Counter()

    for item in data:
        raw_reason = normalize_reason(item.get("missed_reason", ""))

        # This label is a bookkeeping inconsistency and should not be counted
        # as a missed ground-truth bug reason in Section 4.4.1.
        if raw_reason == "detected by us":
            continue

        raw_reason_counter[raw_reason] += 1

        subcategory = RAW_REASON_TO_SUBCATEGORY.get(raw_reason)
        if subcategory is None:
            subcategory = "Incorrect execution"
            unmapped_reasons[raw_reason] += 1

        category = SUBCATEGORY_TO_CATEGORY[subcategory]

        subcategory_counter[subcategory] += 1
        category_counter[category] += 1
        grouped_raw_reasons[subcategory][raw_reason] += 1

        parent_bug_id = item.get("parent_bug_id")
        if parent_bug_id is not None:
            pr_counter[parent_bug_id] += 1

    return {
        "category_counter": category_counter,
        "subcategory_counter": subcategory_counter,
        "raw_reason_counter": raw_reason_counter,
        "grouped_raw_reasons": grouped_raw_reasons,
        "pr_counter": pr_counter,
        "unmapped_reasons": unmapped_reasons,
    }


def print_missed_bug_table(results: Dict[str, object]) -> None:
    category_counter = results["category_counter"]
    subcategory_counter = results["subcategory_counter"]
    grouped_raw_reasons = results["grouped_raw_reasons"]
    unmapped_reasons = results["unmapped_reasons"]

    total = sum(category_counter.values())

    print("\nRQ3: Analysis of Missed Ground-Truth Bugs")
    print("-" * 115)
    print(f"{'Category / Subcategory / Raw reason':<82} {'Count':>8} {'Ratio':>10}")
    print("-" * 115)

    for category, subcategories in RQ3_MISSED_REASON_STRUCTURE.items():
        category_count = category_counter.get(category, 0)
        if category_count == 0:
            continue

        category_ratio = category_count / total * 100 if total else 0.0
        print(f"{category:<82} {category_count:>8} {category_ratio:>9.1f}%")

        for subcategory in subcategories:
            subcategory_count = subcategory_counter.get(subcategory, 0)
            if subcategory_count == 0:
                continue

            print(f"  - {subcategory:<78} {subcategory_count:>8}")

            for raw_reason, count in grouped_raw_reasons[subcategory].most_common():
                print(f"      · {raw_reason:<74} {count:>8}")

        print()

    print("-" * 115)
    print(f"{'Total':<82} {total:>8} {100.0:>9.1f}%")
    print("-" * 115)

    if unmapped_reasons:
        print("\nUnmapped raw reasons grouped under 'Incorrect execution':")
        for reason, count in unmapped_reasons.most_common():
            print(f"  {count:>4}  {reason}")


def print_pr_distribution(results: Dict[str, object]) -> None:
    pr_counter = results["pr_counter"]

    print("\nMissed Ground-Truth Bugs per PR")
    print("-" * 60)
    for pr, count in pr_counter.most_common():
        print(f"PR {pr}: {count} missed bugs")
    print("-" * 60)


def main() -> None:
    results = collect_missed_bug_distribution()
    print_missed_bug_table(results)
    # print_pr_distribution(results)


if __name__ == "__main__":
    main()