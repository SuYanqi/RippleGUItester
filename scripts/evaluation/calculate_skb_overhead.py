#!/usr/bin/env python
"""Calculate SKB (Scenario Knowledge Base) construction overhead.

Run:
    python -m scripts.evaluation.calculate_skb_overhead
"""

import json
from pathlib import Path
from typing import Dict, List, Optional


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "output"
APPS = ["Zettlr", "JabRef", "Godot", "Firefox"]

# Firefox duration: 50.28 hours (estimated from file timestamps in the processing output).
# classify_output.json lacks DURATION_MINS field for Firefox, so duration is estimated
# from the time span of files generated during the SKB construction process.
FIREFOX_ESTIMATED_DURATION_HOURS = 50.28


def load_classify_output(app: str) -> Optional[Dict[str, float]]:
    """Load and analyze classify_output.json for a single app."""
    classify_file = OUTPUT_DIR / app / "classify_output.json"

    if not classify_file.exists():
        return None

    try:
        with open(classify_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return None

    if not isinstance(data, list):
        return None

    total_duration = 0.0
    total_cost = 0.0
    included_count = 0
    has_duration_data = False

    for entry in data:
        # Sum up duration
        if "DURATION_MINS" in entry:
            total_duration += entry["DURATION_MINS"]
            has_duration_data = True

        # Sum up cost
        if "COST" in entry and isinstance(entry["COST"], dict):
            if "total_cost" in entry["COST"]:
                total_cost += entry["COST"]["total_cost"]

        # Count included scenarios
        if entry.get("include_scenario", False):
            included_count += 1

    # Mark if duration data is missing (will be estimated later based on other apps)
    if not has_duration_data:
        total_duration = 0.0  # Will be filled in calculate_all_apps()

    return {
        "app": app,
        "total_entries": len(data),
        "included_count": included_count,
        "excluded_count": len(data) - included_count,
        "duration_mins": total_duration,
        "duration_hours": total_duration / 60,
        "cost": total_cost,
        "has_duration_data": has_duration_data,
    }


def calculate_all_apps() -> List[Dict[str, float]]:
    """Calculate SKB overhead for all apps."""
    results = []

    # Collect all results
    for app in APPS:
        result = load_classify_output(app)
        if result:
            # Special handling for Firefox: use estimated duration from file timestamps
            if app == "Firefox" and not result["has_duration_data"]:
                result["duration_hours"] = FIREFOX_ESTIMATED_DURATION_HOURS
                result["duration_mins"] = FIREFOX_ESTIMATED_DURATION_HOURS * 60
            results.append(result)

    return results


def print_results(results: List[Dict[str, float]]) -> None:
    """Print SKB construction overhead results."""
    if not results:
        print("No classify_output.json files found.")
        return

    print("\nSKB (Scenario Knowledge Base) Construction Overhead")
    print("=" * 70)
    print("\nSKB construction is a one-off activity.\n")
    print(f"{'App':<15} {'Time (hours)':<20} {'Cost':<15}")
    print("-" * 70)

    for r in results:
        print(
            f"{r['app']:<15} "
            f"{r['duration_hours']:<20.2f} "
            f"${r['cost']:<14.2f}"
        )

    # Calculate total
    total_duration = sum(r["duration_hours"] for r in results)
    total_cost = sum(r["cost"] for r in results)

    print("-" * 70)
    print(
        f"{'Total':<15} "
        f"{total_duration:<20.2f} "
        f"${total_cost:<14.2f}"
    )
    print("=" * 70)


def main():
    results = calculate_all_apps()

    if not results:
        print("Error: No classify_output.json files found.")
        print("Expected files:")
        for app in APPS:
            print(f"  - {OUTPUT_DIR / app / 'classify_output.json'}")
        return

    print_results(results)


if __name__ == "__main__":
    main()
