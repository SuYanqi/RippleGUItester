"""
Clear vector stores for a repository.

This script deletes all vector stores and uploaded files from OpenAI for a specific
repository, and removes the local cache file.

Usage:
    python -m scripts.preparation.clear_vector_stores --repo Zettlr
    python -m scripts.preparation.clear_vector_stores --repo JabRef
    python -m scripts.preparation.clear_vector_stores --repo Godot
    python -m scripts.preparation.clear_vector_stores --repo Firefox
"""

import argparse
from src.utils.gpt_util import GPTUtil

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Clear vector stores for a repository"
    )
    parser.add_argument(
        "--repo",
        type=str,
        choices=["Firefox", "Zettlr", "Godot", "JabRef"],
        required=True,
        help="Repository name to clear vector stores for"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Skip confirmation prompt"
    )
    args = parser.parse_args()

    reponame = args.repo

    print(f"\n{'='*70}")
    print(f"Clear Vector Stores for {reponame}")
    print(f"{'='*70}\n")

    # Load existing vector stores
    stores = GPTUtil.load_vector_stores(reponame)

    if not stores:
        print(f"No vector stores found for {reponame}")
        print(f"Local cache file: data/{reponame}/vector_store_ids.json does not exist or is empty")
        exit(0)

    print(f"Found {len(stores)} vector store(s) for {reponame}:")
    for vector_store_name, vector_store_id in stores.items():
        print(f"  • {vector_store_name}")
        print(f"    ID: {vector_store_id}")

    # Confirmation
    if not args.confirm:
        print(f"\n⚠️  WARNING: This will delete:")
        print(f"  1. All vector stores for {reponame} from OpenAI")
        print(f"  2. All uploaded files associated with these vector stores")
        print(f"  3. Local cache file: data/{reponame}/vector_store_ids.json")
        print(f"\nThis action cannot be undone!")

        response = input(f"\nAre you sure you want to delete all vector stores for {reponame}? (yes/no): ")
        if response.lower() != "yes":
            print("Cancelled.")
            exit(0)

    print(f"\nDeleting vector stores...\n")

    # Delete each vector store
    for vector_store_name, vector_store_id in stores.items():
        print(f"Processing: {vector_store_name}")
        print(f"  Vector Store ID: {vector_store_id}")

        # List and delete all files in the vector store
        try:
            files = GPTUtil.client.vector_stores.files.list(vector_store_id=vector_store_id)

            for f in files.data:
                file_id = f.id
                try:
                    # Remove file from vector store
                    GPTUtil.client.vector_stores.files.delete(
                        vector_store_id=vector_store_id,
                        file_id=file_id
                    )
                    print(f"  ✓ Removed file from vector store: {file_id}")

                    # Delete the physical uploaded file
                    GPTUtil.client.files.delete(file_id=file_id)
                    print(f"  ✓ Deleted uploaded file: {file_id}")

                except Exception as e:
                    print(f"  ✗ Error deleting file {file_id}: {e}")
                    continue

        except Exception as e:
            print(f"  ✗ Error listing files: {e}")

        # Delete the vector store itself
        try:
            GPTUtil.client.vector_stores.delete(vector_store_id)
            print(f"  ✓ Deleted vector store: {vector_store_id}\n")

        except Exception as e:
            print(f"  ✗ Error deleting vector store: {e}\n")

    # Delete local cache file
    print("Deleting local cache file...")
    GPTUtil.delete_vector_store_file(reponame)

    print(f"\n{'='*70}")
    print(f"✓ Vector stores cleared for {reponame}")
    print(f"{'='*70}")
    print(f"\nTo recreate vector stores, run:")
    print(f"  python -m scripts.preparation.create_vector_stores --repo {reponame}")
    print()
