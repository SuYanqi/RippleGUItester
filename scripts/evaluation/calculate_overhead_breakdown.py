#!/usr/bin/env python
"""Calculate and visualize overhead breakdown (time and cost) for all apps.

The script supports two data sources:
1. Pre-aggregated summary files (default, recommended) - reads from pre-calculated overhead summaries
2. Raw output JSON files (for validation) - calculates from original detector/replayer/generator/... JSON files

Run:
    python -m scripts.evaluation.calculate_overhead_breakdown                # Use summary files (default)
    python -m scripts.evaluation.calculate_overhead_breakdown --source log   # Use summary files
    python -m scripts.evaluation.calculate_overhead_breakdown --source raw   # Use raw JSON files
"""

import argparse
import json
import os
import platform
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "output"
APPS = ["Firefox", "Zettlr", "JabRef", "Godot"]

# JSON field names (matching the actual structure in JSON files)
DURATION_MINS_UPPER = "DURATION_MINS"
DURATION_MINS_LOWER = "duration (mins)"
COST_UPPER = "COST"
COST_LOWER = "cost"
TOTAL_COST_UNDERSCORE = "total_cost"
TOTAL_COST_SPACE = "total cost"
TOTAL_DURATION_MINS_UPPER = "TOTAL_DURATION_MINS"
TOTAL_DURATION_MINS_LOWER = "total duration (mins)"


# ============================================================================
# Method 1: Parse from aggregated log files (recommended)
# ============================================================================

def parse_overhead_log(log_file: Path) -> Optional[Dict[str, float]]:
    """Parse a 4_0_calculate_duration_time_and_cost_*.txt log file."""
    if not log_file.exists():
        return None

    with open(log_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract repository name
    repo_match = re.search(r'Repository:\s*(\w+)', content)
    if not repo_match:
        return None
    app = repo_match.group(1)

    # Extract PR count
    pr_match = re.search(r'Total PR number:\s*(\d+)', content)
    pr_count = int(pr_match.group(1)) if pr_match else 0

    # Extract Test Scenario Generation
    gen_time_match = re.search(r'\[Test Scenario Generation\].*?Time:\s*([\d.]+)\s*mins', content, re.DOTALL)
    gen_cost_match = re.search(r'\[Test Scenario Generation\].*?Cost:\s*\$([\d.]+)', content, re.DOTALL)

    # Extract Test Scenario Execution
    exec_time_match = re.search(r'\[Test Scenario Execution\].*?Time:\s*([\d.]+)\s*mins', content, re.DOTALL)
    exec_cost_match = re.search(r'\[Test Scenario Execution\].*?Cost:\s*\$([\d.]+)', content, re.DOTALL)

    # Extract Bug Detection
    detect_time_match = re.search(r'\[Bug Detection\].*?Time:\s*([\d.]+)\s*mins', content, re.DOTALL)
    detect_cost_match = re.search(r'\[Bug Detection\].*?Cost:\s*\$([\d.]+)', content, re.DOTALL)

    # Extract Overall
    overall_time_match = re.search(r'\[Overall\].*?Time:\s*([\d.]+)\s*mins', content, re.DOTALL)
    overall_cost_match = re.search(r'\[Overall\].*?Cost:\s*\$([\d.]+)', content, re.DOTALL)

    gen_duration = float(gen_time_match.group(1)) if gen_time_match else 0.0
    gen_cost = float(gen_cost_match.group(1)) if gen_cost_match else 0.0

    exec_duration = float(exec_time_match.group(1)) if exec_time_match else 0.0
    exec_cost = float(exec_cost_match.group(1)) if exec_cost_match else 0.0

    detect_duration = float(detect_time_match.group(1)) if detect_time_match else 0.0
    detect_cost = float(detect_cost_match.group(1)) if detect_cost_match else 0.0

    total_duration = float(overall_time_match.group(1)) if overall_time_match else (gen_duration + exec_duration + detect_duration)
    total_cost = float(overall_cost_match.group(1)) if overall_cost_match else (gen_cost + exec_cost + detect_cost)

    return {
        "app": app,
        "pr_count": pr_count,
        "gen_duration_mins": gen_duration,
        "gen_duration_hours": gen_duration / 60,
        "gen_cost": gen_cost,
        "exec_duration_mins": exec_duration,
        "exec_duration_hours": exec_duration / 60,
        "exec_cost": exec_cost,
        "detect_duration_mins": detect_duration,
        "detect_duration_hours": detect_duration / 60,
        "detect_cost": detect_cost,
        "total_duration_mins": total_duration,
        "total_duration_hours": total_duration / 60,
        "total_cost": total_cost,
    }


def calculate_from_log() -> List[Dict[str, float]]:
    """Calculate overhead for all apps from aggregated log files."""
    results = []
    for app in APPS:
        log_file = OUTPUT_DIR / app / f"calculate_duration_time_and_cost_{app.lower()}.txt"
        result = parse_overhead_log(log_file)
        if result:
            results.append(result)
        else:
            print(f"Warning: Could not parse {log_file}")
    return results


# ============================================================================
# Method 2: Calculate from raw output JSON files
# ============================================================================

def load_json(path: Path):
    """Load a JSON file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return None


def calculate_app_overhead_from_raw(app: str) -> Optional[Dict[str, float]]:
    """Calculate time and cost breakdown for a single app from raw output JSON files."""
    app_output_dir = OUTPUT_DIR / app / "output"

    if not app_output_dir.exists():
        return None

    # Find all PR folders (numeric folder names)
    pr_folders = [
        p for p in app_output_dir.iterdir()
        if p.is_dir() and p.name[0].isdigit()
    ]

    if not pr_folders:
        return None

    # Accumulators
    gen_duration = 0.0
    gen_cost = 0.0
    exec_duration = 0.0
    exec_cost = 0.0
    detect_duration = 0.0
    detect_cost = 0.0

    for pr_folder in pr_folders:
        # ---------- Test Scenario Generation ----------
        for name in ["generator.json", "data_enhancer.json", "path_enhancer.json"]:
            for path in pr_folder.rglob(name):
                output = load_json(path)
                if output and len(output) > 2 and isinstance(output[2], dict):
                    content = output[2].get("content", {})
                    if isinstance(content, dict):
                        # Try uppercase field name
                        if DURATION_MINS_UPPER in content:
                            gen_duration += content[DURATION_MINS_UPPER]
                        # Try lowercase field name
                        elif DURATION_MINS_LOWER in content:
                            gen_duration += content[DURATION_MINS_LOWER]

                        # Cost handling
                        if COST_UPPER in content and isinstance(content[COST_UPPER], dict):
                            gen_cost += content[COST_UPPER].get(TOTAL_COST_UNDERSCORE, 0) or content[COST_UPPER].get(TOTAL_COST_SPACE, 0)
                        elif COST_LOWER in content and isinstance(content[COST_LOWER], dict):
                            gen_cost += content[COST_LOWER].get(TOTAL_COST_UNDERSCORE, 0) or content[COST_LOWER].get(TOTAL_COST_SPACE, 0)

        # ---------- Execution & Detection ----------
        for folder in pr_folder.rglob("*"):
            if not (folder.is_dir() and folder.name[0].isdigit()):
                continue

            # Execution
            replayer = folder / "replayer.json"
            if replayer.exists():
                output = load_json(replayer)
                if output and isinstance(output, dict):
                    # Try both field name variants
                    if DURATION_MINS_UPPER in output:
                        exec_duration += output[DURATION_MINS_UPPER]
                    elif DURATION_MINS_LOWER in output:
                        exec_duration += output[DURATION_MINS_LOWER]

                    if TOTAL_COST_UNDERSCORE in output:
                        exec_cost += output[TOTAL_COST_UNDERSCORE]
                    elif TOTAL_COST_SPACE in output:
                        exec_cost += output[TOTAL_COST_SPACE]

            # Detection
            for detector in folder.glob("detector_*.json"):
                output = load_json(detector)
                if output and isinstance(output, list) and len(output) > 0:
                    last = output[-1]
                    if isinstance(last, dict):
                        # Duration
                        if TOTAL_DURATION_MINS_UPPER in last:
                            detect_duration += last[TOTAL_DURATION_MINS_UPPER]
                        elif TOTAL_DURATION_MINS_LOWER in last:
                            detect_duration += last[TOTAL_DURATION_MINS_LOWER]

                        # Cost
                        if TOTAL_COST_UNDERSCORE in last:
                            detect_cost += last[TOTAL_COST_UNDERSCORE]
                        elif TOTAL_COST_SPACE in last:
                            detect_cost += last[TOTAL_COST_SPACE]

        # ---------- Post-processing (belongs to Detection) ----------
        for path in pr_folder.rglob("post_processor.json"):
            output = load_json(path)
            if output and isinstance(output, dict):
                # Try both field name variants
                if DURATION_MINS_UPPER in output:
                    detect_duration += output[DURATION_MINS_UPPER]
                elif DURATION_MINS_LOWER in output:
                    detect_duration += output[DURATION_MINS_LOWER]

                # Cost handling
                if COST_UPPER in output and isinstance(output[COST_UPPER], dict):
                    detect_cost += output[COST_UPPER].get(TOTAL_COST_UNDERSCORE, 0) or output[COST_UPPER].get(TOTAL_COST_SPACE, 0)
                elif COST_LOWER in output and isinstance(output[COST_LOWER], dict):
                    detect_cost += output[COST_LOWER].get(TOTAL_COST_UNDERSCORE, 0) or output[COST_LOWER].get(TOTAL_COST_SPACE, 0)

    total_duration = gen_duration + exec_duration + detect_duration
    total_cost = gen_cost + exec_cost + detect_cost

    return {
        "app": app,
        "pr_count": len(pr_folders),
        "gen_duration_mins": gen_duration,
        "gen_duration_hours": gen_duration / 60,
        "gen_cost": gen_cost,
        "exec_duration_mins": exec_duration,
        "exec_duration_hours": exec_duration / 60,
        "exec_cost": exec_cost,
        "detect_duration_mins": detect_duration,
        "detect_duration_hours": detect_duration / 60,
        "detect_cost": detect_cost,
        "total_duration_mins": total_duration,
        "total_duration_hours": total_duration / 60,
        "total_cost": total_cost,
    }


def calculate_from_raw() -> List[Dict[str, float]]:
    """Calculate overhead for all apps from raw output JSON files."""
    results = []
    for app in APPS:
        result = calculate_app_overhead_from_raw(app)
        if result:
            results.append(result)
    return results


# ============================================================================
# Common functions for both methods
# ============================================================================

def print_results(results: List[Dict[str, float]]) -> None:
    """Print overhead breakdown results."""
    if not results:
        print("No data found. Please check the data source.")
        return

    # Aggregate totals
    total_pr = sum(r["pr_count"] for r in results)
    total_gen_duration = sum(r["gen_duration_hours"] for r in results)
    total_gen_cost = sum(r["gen_cost"] for r in results)
    total_exec_duration = sum(r["exec_duration_hours"] for r in results)
    total_exec_cost = sum(r["exec_cost"] for r in results)
    total_detect_duration = sum(r["detect_duration_hours"] for r in results)
    total_detect_cost = sum(r["detect_cost"] for r in results)
    total_duration = sum(r["total_duration_hours"] for r in results)
    total_cost = sum(r["total_cost"] for r in results)

    def pct(x, total):
        return (x / total * 100.0) if total > 0 else 0.0

    def format_cost(cost):
        """Format cost to 3 significant figures."""
        if cost >= 100:
            return f"${cost:.1f}"
        elif cost >= 10:
            return f"${cost:.2f}"
        else:
            return f"${cost:.3f}"

    print("\nOverhead Breakdown Analysis")
    print("=" * 80)

    # Overall breakdown (moved to top)
    print(f"\nOverall ({total_pr} PRs):")
    print("\n  Test Scenario Generation:")
    print(f"    Time: {total_gen_duration:.1f} hours ({pct(total_gen_duration, total_duration):.1f}%)")
    print(f"    Cost: {format_cost(total_gen_cost)} ({pct(total_gen_cost, total_cost):.1f}%)")

    print("\n  Test Scenario Execution:")
    print(f"    Time: {total_exec_duration:.1f} hours ({pct(total_exec_duration, total_duration):.1f}%)")
    print(f"    Cost: {format_cost(total_exec_cost)} ({pct(total_exec_cost, total_cost):.1f}%)")

    print("\n  Bug Detection:")
    print(f"    Time: {total_detect_duration:.1f} hours ({pct(total_detect_duration, total_duration):.1f}%)")
    print(f"    Cost: {format_cost(total_detect_cost)} ({pct(total_detect_cost, total_cost):.1f}%)")

    print("\n  Total:")
    print(f"    Time: {total_duration:.1f} hours")
    print(f"    Cost: {format_cost(total_cost)}")

    # Average per PR
    avg_duration = total_duration / total_pr if total_pr > 0 else 0
    avg_cost = total_cost / total_pr if total_pr > 0 else 0
    print(f"\n  Average per PR:")
    print(f"    Time: {avg_duration:.1f} hours ({avg_duration * 60:.1f} mins)")
    print(f"    Cost: {format_cost(avg_cost)}")

    # Per-app breakdown
    print("\n" + "=" * 80)
    print("Per-App Breakdown:")
    print("=" * 80)

    for r in results:
        print(f"\n{r['app']} ({r['pr_count']} PRs):")
        print("  Test Scenario Generation:")
        print(f"    Time: {r['gen_duration_hours']:.1f} hours ({pct(r['gen_duration_hours'], r['total_duration_hours']):.1f}%)")
        print(f"    Cost: {format_cost(r['gen_cost'])} ({pct(r['gen_cost'], r['total_cost']):.1f}%)")

        print("  Test Scenario Execution:")
        print(f"    Time: {r['exec_duration_hours']:.1f} hours ({pct(r['exec_duration_hours'], r['total_duration_hours']):.1f}%)")
        print(f"    Cost: {format_cost(r['exec_cost'])} ({pct(r['exec_cost'], r['total_cost']):.1f}%)")

        print("  Bug Detection:")
        print(f"    Time: {r['detect_duration_hours']:.1f} hours ({pct(r['detect_duration_hours'], r['total_duration_hours']):.1f}%)")
        print(f"    Cost: {format_cost(r['detect_cost'])} ({pct(r['detect_cost'], r['total_cost']):.1f}%)")

        print("  Total:")
        print(f"    Time: {r['total_duration_hours']:.1f} hours")
        print(f"    Cost: {format_cost(r['total_cost'])}")

    print("=" * 80)


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
            print(f"  Opened in VS Code: {file_path}")
            return

        # Fallback to system default
        system = platform.system()
        if system == "Darwin":  # macOS
            subprocess.run(["open", str(file_path)], check=False)
        elif system == "Windows":
            os.startfile(str(file_path))
        elif system == "Linux":
            subprocess.run(["xdg-open", str(file_path)], check=False)
        print(f"  Opened: {file_path}")
    except Exception as e:
        print(f"  Could not auto-open file: {e}")


def visualize_results(results: List[Dict[str, float]]) -> None:
    """Create visualization of overhead breakdown following labeling/4_1_draw_plot.py style."""
    if not results:
        return

    # Calculate overall percentages
    total_gen_duration = sum(r["gen_duration_hours"] for r in results)
    total_exec_duration = sum(r["exec_duration_hours"] for r in results)
    total_detect_duration = sum(r["detect_duration_hours"] for r in results)
    total_duration = total_gen_duration + total_exec_duration + total_detect_duration

    total_gen_cost = sum(r["gen_cost"] for r in results)
    total_exec_cost = sum(r["exec_cost"] for r in results)
    total_detect_cost = sum(r["detect_cost"] for r in results)
    total_cost = total_gen_cost + total_exec_cost + total_detect_cost

    # Calculate percentages
    time_pct = [
        (total_gen_duration / total_duration * 100) if total_duration > 0 else 0,
        (total_exec_duration / total_duration * 100) if total_duration > 0 else 0,
        (total_detect_duration / total_duration * 100) if total_duration > 0 else 0,
    ]

    cost_pct = [
        (total_gen_cost / total_cost * 100) if total_cost > 0 else 0,
        (total_exec_cost / total_cost * 100) if total_cost > 0 else 0,
        (total_detect_cost / total_cost * 100) if total_cost > 0 else 0,
    ]

    # Phase names
    phases = ["Test Scenario Generator", "Test Scenario Executor", "Bug Detector"]

    # Colors matching the Venn diagram style
    colors = ["#E3E3E3", "#F6D6DE", "#E9A9BC"]

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 2.1))

    # Draw Execution Time bar
    left = 0
    for pct, color in zip(time_pct, colors):
        ax.barh("Time", pct, left=left, color=color, linewidth=0.6)
        left += pct

    # Draw Monetary Cost bar
    left = 0
    for pct, color in zip(cost_pct, colors):
        ax.barh("Cost", pct, left=left, color=color, linewidth=0.6)
        left += pct

    # Axis formatting
    ax.set_xlim(0, 100)
    ax.set_xlabel("Percentage (%)")
    ax.set_ylabel("")  # Hide y-axis label
    ax.grid(axis="x", linestyle="--", alpha=0.4)

    # Legend (order and colors match the figure)
    handles = [plt.Rectangle((0, 0), 1, 1, facecolor=c) for c in colors]
    ax.legend(
        handles,
        phases,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.32),  # Position above the plot
        ncol=3,
        frameon=False,
    )

    # Add text annotations
    def annotate_bar(y, values, text_color="#444444"):
        left = 0
        for v in values:
            ax.text(
                left + v / 2,  # Place text at the center of the segment
                y,
                f"{v:.1f}%",
                ha="center",
                va="center",
                fontsize=9,
                color=text_color,
            )
            left += v  # Move to the next segment

    annotate_bar("Time", time_pct)
    annotate_bar("Cost", cost_pct)

    plt.tight_layout()

    # Save figure to output directory (both PDF and PNG)
    output_pdf = OUTPUT_DIR / "overhead_breakdown.pdf"
    output_png = OUTPUT_DIR / "overhead_breakdown.png"

    plt.savefig(output_pdf)
    plt.savefig(output_png, dpi=300, bbox_inches='tight')

    print(f"\nVisualization saved to:")
    print(f"  PDF: {output_pdf}")
    print(f"  PNG: {output_png}")

    # Auto-open the PNG file
    if output_png.exists():
        open_file(output_png)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Calculate overhead breakdown from aggregated log files or raw output JSON files"
    )
    parser.add_argument(
        "--source",
        choices=["log", "raw"],
        default="log",
        help="Data source: 'log' for aggregated log files (default), 'raw' for raw output JSON files"
    )
    args = parser.parse_args()

    print(f"Data source: {args.source.upper()}")
    print("-" * 80)

    if args.source == "log":
        results = calculate_from_log()
    else:
        results = calculate_from_raw()

    print_results(results)
    visualize_results(results)


if __name__ == "__main__":
    main()
