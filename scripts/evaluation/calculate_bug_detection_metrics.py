#!/usr/bin/env python
"""Calculate Table 1 metrics from output annotation results.

This script computes bug detection metrics including TP, FP, Precision, and Bug#
for all evaluated applications. It reads from detector_output_evaluation and
detector_output_tp_dedup directories.

Run:
    python -m scripts.evaluation.calculate_bug_detection_metrics
"""

# =============================================================================
# CALCULATION LOGIC
# =============================================================================
#
# 1. True Positives (TP):
#    - Count ALL bugs where is_true_positive=True
#    - The tool successfully detected real bugs
#
# 2. Bug# (Unique Bugs):
#    - For Firefox: Bug# = dedup_tp - known_ground_truth_count
#    - For other apps: Bug# = dedup_tp
#    - Represents unique bugs discovered by the tool after deduplication
#    - For Firefox, subtract known ground truth bugs to get truly novel discoveries
#
# 3. Precision:
#    - Precision = TP / (TP + FP)
#    - FP = Total Detections - TP
#
# =============================================================================

import json
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "output"
APPS = ["Firefox", "Zettlr", "JabRef", "Godot"]


def load_detector_evaluation(app: str) -> Dict[str, int]:
    app_dir = OUTPUT_DIR / app
    eval_dir = app_dir / "detector_output_evaluation"
    if not eval_dir.exists():
        raise FileNotFoundError(f"Missing evaluation directory: {eval_dir}")

    total_detections = 0
    tp_count = 0

    for path in sorted(eval_dir.glob("*_detector_labels.json")):
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        for scenario in data.get("test_scenarios", []):
            for bug in scenario.get("discovered_bugs", []):
                total_detections += 1
                if bug.get("is_true_positive"):
                    tp_count += 1

    return {
        "total_detections": total_detections,
        "tp_count": tp_count,
    }


def load_pr_count(app: str) -> int:
    app_dir = OUTPUT_DIR / app
    eval_dir = app_dir / "detector_output_evaluation"
    if not eval_dir.exists():
        return 0
    return sum(1 for _ in eval_dir.glob("*_detector_labels.json"))


def load_dedup_bug_count(app: str) -> int:
    """Count unique bugs from tp_dedup."""
    app_dir = OUTPUT_DIR / app
    dedup_dir = app_dir / "detector_output_tp_dedup"
    if not dedup_dir.exists():
        return 0

    bug_count = 0
    for path in sorted(dedup_dir.glob("*_tp_dedup_labels.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        for scenario in data.get("test_scenarios", []):
            for bug in scenario.get("discovered_bugs", []):
                if bug.get("is_duplicate") is not True:
                    bug_count += 1

    return bug_count


def load_detected_introduced_bug_count(app: str) -> int:
    app_dir = OUTPUT_DIR / app
    label_file = app_dir / "introduced_bug_labels.json"
    if not label_file.exists():
        return 0

    try:
        data = json.loads(label_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return 0

    return sum(1 for item in data if item.get("detected_by_us", False))


def format_percent(num: float) -> str:
    return f"{num * 100:.1f}%" if num is not None else "0.0%"


def calculate_table1() -> List[Dict[str, object]]:
    results = []
    for app in APPS:
        eval_stats = load_detector_evaluation(app)
        pr_count = load_pr_count(app)
        tp = eval_stats["tp_count"]
        dedup_tp = load_dedup_bug_count(app)

        # Normal calculation for all apps (no special handling for pre-existing bugs)
        if app == "Firefox":
            detected_introduced = load_detected_introduced_bug_count(app)
            # Bug# calculation: dedup_tp - known_ground_truth
            bug_count = max(0, dedup_tp - detected_introduced)
            note = f"Bug#: {dedup_tp} dedup - {detected_introduced} known GT = {bug_count}"
        else:
            bug_count = dedup_tp
            note = ""

        total = eval_stats["total_detections"]
        fp = total - tp
        precision = tp / total if total > 0 else 0.0

        results.append(
            {
                "app": app,
                "pr_count": pr_count,
                "bug_count": bug_count,
                "tp": tp,
                "fp": fp,
                "precision": precision,
                "total_detections": total,
                "notes": note,
            }
        )
    return results


def print_results(results: List[Dict[str, object]]) -> None:
    total_pr = sum(r["pr_count"] for r in results)
    total_bug = sum(r["bug_count"] for r in results)
    total_tp = sum(r["tp"] for r in results)
    total_fp = sum(r["fp"] for r in results)
    total_detections = sum(r["total_detections"] for r in results)
    total_prec = total_tp / (total_tp + total_fp) if total_tp + total_fp > 0 else 0.0

    print("Table 1. Bug Detection")
    print("-------------------------------------------------------------------------------")
    print(
        f"{'App':<10} {'PR#':>4} {'Bug#':>5} {'TP':>6} {'FP':>6} {'Precision':>10} {'Detections':>12}"
    )
    print("-------------------------------------------------------------------------------")
    for r in results:
        print(
            f"{r['app']:<10} {r['pr_count']:>4} {r['bug_count']:>5} {r['tp']:>6} {r['fp']:>6} {r['precision']:>10.3f} {r['total_detections']:>12}"
        )
    print("-------------------------------------------------------------------------------")
    print(
        f"{'Total':<10} {total_pr:>4} {total_bug:>5} {total_tp:>6} {total_fp:>6} {total_prec:>10.3f} {total_detections:>12}"
    )
    print("-------------------------------------------------------------------------------")


if __name__ == '__main__':
    results = calculate_table1()
    print_results(results)
