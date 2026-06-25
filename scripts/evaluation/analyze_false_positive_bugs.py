#!/usr/bin/env python
"""Reproduce RQ2 false-positive distribution analysis.

Run:
    python -m scripts.evaluation.analyze_false_positive_bugs
"""

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "output"
APPS = ["Firefox", "Zettlr", "JabRef", "Godot"]

RQ2_STRUCTURE = {
    "GUI Rendering and Temporal Instability": [
        "Screenshot timing or rendering delay",
        "Unstable GUI layout/rendering",
    ],
    "LLM Reasoning and Hallucination Errors": [
        "LLM hallucination — misinterpreted or imagined GUI rendering",
        "LLM hallucination — predicted an non-executed action as executed",
        "Unreasonable or unnecessary improvement suggestion, not a real issue",
    ],
    "GUI Interaction and Replay Instability": [
        "GUI element location or interaction error (non-deterministic behavior)",
        "UI layout shift leading to incorrect replay click",
        "Code-induced GUI difference leading to replay mismatch",
    ],
    "Expected GUI Differences due to Code Changes": [
        "Expected GUI difference due to intended code change",
    ],
    "Others": [
        "Unstable test data causing GUI inconsistency during replay",
        "Uncertain whether true positive or false positive",
    ],
}

REASON_TO_CATEGORY = {
    reason: category
    for category, reasons in RQ2_STRUCTURE.items()
    for reason in reasons
}


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"⚠️ Skipping invalid JSON: {path}")
        return None


def normalize_reason(reason) -> str:
    if isinstance(reason, dict):
        reason = reason.get("value", "")
    elif reason is None:
        reason = ""
    elif not isinstance(reason, str):
        reason = str(reason)

    reason = reason.strip()
    return reason if reason else "Uncertain whether true positive or false positive"


def load_detector_results(app: str) -> List[dict]:
    eval_dir = OUTPUT_DIR / app / "detector_output_evaluation"
    if not eval_dir.exists():
        raise FileNotFoundError(f"Missing evaluation directory: {eval_dir}")

    results = []
    for path in sorted(eval_dir.glob("*_detector_labels.json")):
        data = load_json(path)
        if data is not None:
            results.append(data)
    return results


def collect_false_positive_reasons() -> Counter:
    reason_counter = Counter()

    for app in APPS:
        for result in load_detector_results(app):
            for scenario in result.get("test_scenarios", []):
                for bug in scenario.get("discovered_bugs", []):
                    if bug.get("is_duplicate", False):
                        continue

                    if bug.get("is_true_positive") is False:
                        reasons = bug.get("false_positive_reasons", [])

                        if not reasons:
                            reason_counter[
                                "Uncertain whether true positive or false positive"
                            ] += 1
                            continue

                        for reason in reasons:
                            reason_counter[normalize_reason(reason)] += 1

    return reason_counter


def group_reasons(reason_counter: Counter):
    category_counter = Counter()
    grouped_reasons = defaultdict(Counter)
    unmapped_reasons = Counter()

    for reason, count in reason_counter.items():
        category = REASON_TO_CATEGORY.get(reason)

        if category is None:
            category = "Others"
            unmapped_reasons[reason] += count

        category_counter[category] += count
        grouped_reasons[category][reason] += count

    return category_counter, grouped_reasons, unmapped_reasons


def print_rq2_table(
    category_counter: Counter,
    grouped_reasons: Dict[str, Counter],
    unmapped_reasons: Counter,
) -> None:
    total = sum(category_counter.values())

    print("\nRQ2: False Positive Distribution")
    print("-" * 110)
    print(f"{'Category / Subcategory':<78} {'Count':>8} {'Ratio':>10}")
    print("-" * 110)

    for category, subcategories in RQ2_STRUCTURE.items():
        category_count = category_counter.get(category, 0)
        if category_count == 0:
            continue

        ratio = category_count / total * 100 if total else 0.0
        print(f"{category:<78} {category_count:>8} {ratio:>9.1f}%")

        for subcategory in subcategories:
            count = grouped_reasons[category].get(subcategory, 0)
            if count > 0:
                print(f"  - {subcategory:<74} {count:>8} {'':>10}")

        print()

    print("-" * 110)
    print(f"{'Total':<78} {total:>8} {100.0:>9.1f}%")
    print("-" * 110)

    if unmapped_reasons:
        print("\nUnmapped reasons grouped under Others:")
        for reason, count in unmapped_reasons.most_common():
            print(f"  {count:>4}  {reason}")


def main() -> None:
    reason_counter = collect_false_positive_reasons()
    category_counter, grouped_reasons, unmapped_reasons = group_reasons(reason_counter)
    print_rq2_table(category_counter, grouped_reasons, unmapped_reasons)


if __name__ == "__main__":
    main()