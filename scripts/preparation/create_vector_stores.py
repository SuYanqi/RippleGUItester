"""
Create vector stores for any repository's Scenario Knowledge Base (SKB).

This script uploads knowledge base files to OpenAI and creates vector stores
for use during testing. Only needs to be run once per repository.

Usage:
    python -m scripts.preparation.create_vector_stores --repo Zettlr
    python -m scripts.preparation.create_vector_stores --repo JabRef
    python -m scripts.preparation.create_vector_stores --repo Godot
    python -m scripts.preparation.create_vector_stores --repo Firefox
"""

import argparse
import re
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
from src.utils.gpt_util import GPTUtil
from config import DATA_DIR

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Create vector stores for a repository's Scenario Knowledge Base"
    )
    parser.add_argument(
        "--repo",
        type=str,
        choices=["Firefox", "Zettlr", "Godot", "JabRef"],
        required=True,
        help="Repository name to create vector stores for"
    )
    args = parser.parse_args()

    reponame = args.repo
    knowledge_base_foldername = "knowledge_base"
    output_filepath = Path(DATA_DIR, reponame, knowledge_base_foldername)

    print(f"\n{'='*70}")
    print(f"Creating Vector Stores for {reponame}")
    print(f"{'='*70}\n")

    file_infos = []  # [(filepath, datetime), ...]

    # Step 1: collect all file paths and their datetime
    if output_filepath.exists() and output_filepath.is_dir():
        for filepath in output_filepath.iterdir():
            if filepath.is_file() and filepath.suffix == ".json":
                match = re.search(r"(\d{4}-\d{2}-\d{2}[ _]\d{2}[:\-]\d{2}[:\-]\d{2})", filepath.name)
                if match:
                    file_datetime = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")
                    file_infos.append((filepath, file_datetime))
                else:
                    print(f"⚠️  No date found in filename: {filepath.name}")
    else:
        print(f"❌ Error: Directory {output_filepath} does not exist.")
        print(f"\nPlease ensure you have downloaded the data:")
        print(f"  curl -L -O https://github.com/SuYanqi/RippleGUItester/releases/download/data/data.zip")
        print(f"  unzip data.zip")
        exit(1)

    # Sort by datetime ascending (oldest -> newest)
    file_infos.sort(key=lambda x: x[1])

    print(f"Found {len(file_infos)} knowledge base files for {reponame}\n")

    if not file_infos:
        print(f"❌ No knowledge base files found in {output_filepath}")
        exit(1)

    # Step 2: create vector stores
    file_ids = []
    vector_store_names = []
    stores = GPTUtil.load_vector_stores(reponame)

    print(f"Starting vector store creation (this may take several minutes)...\n")

    for filepath, dt in tqdm(file_infos, desc="Creating vector stores", ascii=True):
        print(f"\n📄 Processing: {filepath.name}")
        print(f"   Date: {dt}")

        # Upload file to OpenAI
        file_id = GPTUtil.create_file(str(filepath))
        file_ids.append(file_id)

        # Create vector store
        vector_store_name = f"{reponame}_{knowledge_base_foldername}_{dt.isoformat()}"
        vector_store_names.append(vector_store_name)

        print(f"   Creating vector store: {vector_store_name}")
        vector_store_id = GPTUtil.create_vector_store_by_name(vector_store_name)

        # Add all accumulated files to this vector store
        for file_id in file_ids:
            GPTUtil.add_file_to_vector_store(vector_store_id, file_id)

        # Save to local cache
        stores[vector_store_name] = vector_store_id
        GPTUtil.save_vector_stores(stores, reponame)

        print(f"   ✓ Vector store created: {vector_store_id}")

    # Summary
    print(f"\n{'='*70}")
    print(f"✓ Successfully created {len(vector_store_names)} vector stores for {reponame}")
    print(f"{'='*70}")
    print(f"\nVector store IDs saved to: data/{reponame}/vector_store_ids.json")

    print()
