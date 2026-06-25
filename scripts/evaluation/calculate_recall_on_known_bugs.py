#!/usr/bin/env python
"""Reproduce RQ3 Venn diagram: Recall on Previously Known Regression Bugs.

This script reproduces the Firefox Venn diagram used in RQ3.

Run:
    python -m scripts.evaluation.calculate_recall_on_known_bugs
"""

import json
import os
import platform
import subprocess
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib_venn import venn2


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "output"
APP = "Firefox"

LOG_BUG_TYPE = "Crash / stack trace / error log"
DUPLICATE_STATUS = "Invalid: Duplicate"

# Log/stack-trace bugs:
# Most log-described bugs are excluded because their reports do not provide
# enough information to reliably map them to concrete GUI behavior.
#
# Bug 1941184 is retained even though it is log-described, because its report
# contains enough information for annotators to understand the corresponding
# bug behavior.
RETAINED_LOG_BUG_IDS = {
    1941184,
}

# Duplicate bugs:
# 1970237 and 1967197 are excluded because their duplicate target bugs are
# already included in the introduced-bug set. Keeping them would double-count
# the same underlying regression.
#
# Bug 1941177 is retained. Although it is labeled as Duplicate in Bugzilla,
# its duplicated target bug was fixed but is not included in the introduced-bug
# set. Therefore, it still represents a distinct evaluable fixed bug for RQ3.
EXCLUDED_DUPLICATE_BUG_IDS = {
    1970237,
    1967197,
}


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON file: {path}") from exc


def load_firefox_introduced_bug_labels():
    label_file = OUTPUT_DIR / APP / "introduced_bug_labels.json"
    if not label_file.exists():
        raise FileNotFoundError(f"Missing label file: {label_file}")
    return load_json(label_file)


def load_dedup_tp_count() -> int:
    """Count unique TP bugs detected by RippleGUItester.

    The detector_output_tp_dedup labels already remove duplicate detections
    produced by the tool.
    """
    dedup_dir = OUTPUT_DIR / APP / "detector_output_tp_dedup"
    if not dedup_dir.exists():
        raise FileNotFoundError(f"Missing dedup directory: {dedup_dir}")

    count = 0
    for path in sorted(dedup_dir.glob("*_tp_dedup_labels.json")):
        data = load_json(path)
        for scenario in data.get("test_scenarios", []):
            for bug in scenario.get("discovered_bugs", []):
                if bug.get("is_duplicate") is not True:
                    count += 1
    return count


def count_pre_existing_bugs() -> int:
    """Count pre-existing bugs (is_introduced=False) from evaluation data."""
    eval_dir = OUTPUT_DIR / APP / "detector_output_evaluation"
    if not eval_dir.exists():
        return 0

    count = 0
    for path in sorted(eval_dir.glob("*_detector_labels.json")):
        data = load_json(path)
        for scenario in data.get("test_scenarios", []):
            for bug in scenario.get("discovered_bugs", []):
                if bug.get("is_true_positive") and bug.get("is_introduced") is False:
                    count += 1
    return count


def count_detected_invalid_ground_truth_labels(labels) -> int:
    """Count detected bugs whose Firefox ground-truth label is invalid.

    This is used only for the Table-1-style unique TP adjustment. It does not
    decide which bugs belong to the RQ3 ground-truth set.
    """
    return sum(
        1
        for item in labels
        if item.get("detected_by_us", False)
        and item.get("bug_status", "").startswith("Invalid")
    )


def is_rq3_ground_truth_bug(item) -> bool:
    """Return whether an introduced bug is included in the RQ3 ground truth.

    Paper protocol:
    - Firefox has 54 introduced bugs associated with the selected PRs.
    - 7 bugs are primarily described through crash logs or stack traces.
      Six are excluded because their reports do not provide enough information
      to reliably infer the corresponding GUI behavior. Bug 1941184 is retained.
    - 3 bugs are marked as Duplicate in Bugzilla. Two are excluded because their
      duplicate target bugs are already included in the introduced-bug set.
      Bug 1941177 is retained because its duplicate target bug was fixed but is
      not separately included in the introduced-bug set.

    Final RQ3 ground-truth size:
        54 - 6 log-described bugs - 2 duplicate-counted bugs = 46
    """
    bug_id = int(item.get("introduced_bug_id"))
    bug_type = item.get("bug_type", "")
    bug_status = item.get("bug_status", "")

    if bug_type == LOG_BUG_TYPE and bug_id not in RETAINED_LOG_BUG_IDS:
        return False

    if bug_status == DUPLICATE_STATUS and bug_id in EXCLUDED_DUPLICATE_BUG_IDS:
        return False

    return True


def calculate_rq3_counts():
    labels = load_firefox_introduced_bug_labels()

    ground_truth = {
        int(item["introduced_bug_id"])
        for item in labels
        if is_rq3_ground_truth_bug(item)
    }

    detected_ground_truth = {
        int(item["introduced_bug_id"])
        for item in labels
        if is_rq3_ground_truth_bug(item)
        and item.get("detected_by_us", False)
    }

    invalid_detected = count_detected_invalid_ground_truth_labels(labels)
    pre_existing = count_pre_existing_bugs()

    # Adjust unique TP count:
    # - Remove pre-existing bugs (present in both pre- and post-change versions)
    # Note: Do NOT remove invalid_detected here - it's only used for ground truth filtering
    unique_detected_tp = load_dedup_tp_count() - pre_existing

    overlap = len(detected_ground_truth)
    our_only = unique_detected_tp - overlap
    gt_only = len(ground_truth) - overlap

    return {
        "unique_detected_tp": unique_detected_tp,
        "ground_truth": len(ground_truth),
        "overlap": overlap,
        "our_only": our_only,
        "gt_only": gt_only,
        "invalid_detected_removed": invalid_detected,
        "pre_existing_removed": pre_existing,
    }


def draw_venn(counts):
    fig, ax = plt.subplots(figsize=(4.5, 3))

    v = venn2(
        subsets=(
            counts["our_only"],
            counts["gt_only"],
            counts["overlap"],
        ),
        set_labels=("Our Approach", "Ground Truth"),
        ax=ax,
    )

    # Colors matching the paper figure
    v.get_patch_by_id("10").set_color("#F6E4E8")  # left
    v.get_patch_by_id("01").set_color("#E1E1E1")  # right
    v.get_patch_by_id("11").set_color("#EFD5DC")  # overlap

    for pid in ["10", "01", "11"]:
        patch = v.get_patch_by_id(pid)
        if patch is not None:
            patch.set_alpha(0.85)

    # Title
    ax.set_title(
        "Overlap between Bugs Detected by Our Approach (TPs)\n"
        "and Ground-Truth Introduced Bugs",
        fontsize=11,
    )

    # Figure explanation
    ax.text(
        0.5,
        -0.18,
        "Left: bugs detected by our approach (true positives only)\n"
        "Right: ground-truth introduced bugs documented in the issue tracker",
        ha="center",
        va="top",
        fontsize=9,
        transform=ax.transAxes,
    )

    # Flatten the Venn diagram to match the paper
    ax.set_aspect(0.22)

    plt.tight_layout()

    output_dir = OUTPUT_DIR / APP
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = output_dir / "firefox_groundtruth_venn.pdf"
    png_path = output_dir / "firefox_groundtruth_venn.png"

    plt.savefig(pdf_path, bbox_inches="tight")
    plt.savefig(png_path, bbox_inches="tight", dpi=300)

    print("Saved Venn diagram to:")
    print(f"  {pdf_path}")
    print(f"  {png_path}")

    return png_path


def open_file(file_path: Path):
    """Open file with the system's default application or VS Code."""
    try:
        # Try using VS Code (works in Dev Container)
        result = subprocess.run(
            ["code", str(file_path)],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"\nOpened in VS Code: {file_path}")
            return

        # Fallback to system default
        system = platform.system()
        if system == "Darwin":  # macOS
            subprocess.run(["open", str(file_path)], check=False)
        elif system == "Windows":
            os.startfile(str(file_path))
        elif system == "Linux":
            subprocess.run(["xdg-open", str(file_path)], check=False)
        print(f"\nOpened: {file_path}")
    except Exception as e:
        print(f"\nCould not auto-open file: {e}")
        print(f"Please open manually: {file_path}")


def main():
    counts = calculate_rq3_counts()

    print("\nRQ3: Firefox Known Regression Recall Venn Counts")
    print("-" * 70)
    print(f"Unique TP bugs detected by RippleGUItester: {counts['unique_detected_tp']}")
    print(f"Ground-truth introduced bugs used for evaluation: {counts['ground_truth']}")
    print(f"Our approach only: {counts['our_only']}")
    print(f"Overlap: {counts['overlap']}")
    print(f"Ground truth only: {counts['gt_only']}")
    print("-" * 70)

    png_path = draw_venn(counts)

    # Auto-open the generated PNG file
    if png_path and png_path.exists():
        open_file(png_path)


if __name__ == "__main__":
    main()