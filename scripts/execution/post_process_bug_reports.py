import json
import argparse
from pathlib import Path

from src.pipelines.post_processor import PostProcessor
from config import APP_NAME_ZETTLR, OUTPUT_DIR, APP_NAME_JABREF, APP_NAME_GODOT, APP_NAME_FIREFOX

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Post-process bug reports from RippleGUItester output")
    parser.add_argument(
        "--repo",
        type=str,
        choices=["Firefox", "Zettlr", "Godot", "JabRef"],
        required=True,
        help="Repository name to process"
    )
    parser.add_argument(
        "--pr",
        type=int,
        help="Specific PR/bug number to process (optional, default: process all)"
    )
    args = parser.parse_args()

    # Map repo name to config constants
    repo_map = {
        "Firefox": APP_NAME_FIREFOX,
        "Zettlr": APP_NAME_ZETTLR,
        "Godot": APP_NAME_GODOT,
        "JabRef": APP_NAME_JABREF
    }
    reponame = repo_map[args.repo]
    specific_pr = args.pr

    print(f"\n{'='*70}")
    print(f"Post-Processing Bug Reports - {args.repo}")
    if specific_pr:
        print(f"Target: PR/Bug #{specific_pr}")
    print(f"{'='*70}\n")

    # Updated path: output/{repo}/output/
    repo_output_path = Path(OUTPUT_DIR, reponame, "output")

    # Check if output directory exists
    if not repo_output_path.exists():
        print(f"❌ Error: Output directory does not exist: {repo_output_path}")
        print(f"Please run 'python -m scripts.execution.app --repo {args.repo}' first to generate output.")
        exit(1)

    # Get all PR/bug folders (numeric directories)
    if specific_pr:
        # Process only the specified PR
        pr_folders = [Path(repo_output_path, str(specific_pr))]
        if not pr_folders[0].exists():
            print(f"❌ Error: No output found for PR/bug #{specific_pr}")
            available_prs = [int(p.name) for p in repo_output_path.iterdir() if p.is_dir() and p.name.isdigit()]
            if available_prs:
                print(f"Available PRs: {sorted(available_prs)}")
            exit(1)
    else:
        # Process all PR folders
        pr_folders = sorted(
            (p for p in repo_output_path.iterdir() if p.is_dir() and p.name.isdigit()),
            key=lambda p: int(p.name),
            reverse=True
        )
        if not pr_folders:
            print(f"❌ Error: No output folders found in {repo_output_path}")
            exit(1)

    print(f"Found {len(pr_folders)} PR(s) to process\n")

    # Process each PR folder
    for pr_folder in pr_folders:
        print(f"\n{'─'*70}")
        print(f"Processing PR/Bug #{pr_folder.name}")
        print(f"{'─'*70}")

        # Find generator_* subdirectories (these contain the actual test outputs)
        generator_dirs = sorted(
            [p for p in pr_folder.iterdir() if p.is_dir() and p.name.startswith("generator_")],
            key=lambda p: p.name,
            reverse=True
        )

        if not generator_dirs:
            print(f"⚠️  No generator_* directories found in {pr_folder}")
            continue

        # Process each generator output (usually there's one per run)
        for gen_dir in generator_dirs:
            print(f"\n  Processing: {gen_dir.name}")
            try:
                # Pass the generator directory directly
                output = PostProcessor.filter_bugs(gen_dir)
                print(f"\n  Results:")
                print(json.dumps(output, indent=2))
                print(f"\n  ✅ Saved to: {gen_dir / 'post_processor.json'}")
            except Exception as e:
                print(f"  ❌ Error processing {gen_dir.name}: {e}")

    print(f"\n{'='*70}")
    print("Post-processing complete!")
    print(f"{'='*70}\n")


