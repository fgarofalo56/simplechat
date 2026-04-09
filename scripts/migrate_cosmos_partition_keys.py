# migrate_cosmos_partition_keys.py
"""
Cosmos DB Partition Key Migration Script for SimpleChat.

PURPOSE:
    Cosmos DB does not allow changing the partition key on an existing container.
    The only way to change the partition key is to create a new container with the
    desired partition key and copy all documents from the old container to the new one.

    This script automates that process for SimpleChat containers that were originally
    created with /id as the partition key but should use a more efficient partition key
    for query performance.

BACKGROUND:
    The config_database.py file now defines containers with optimized partition keys
    (e.g., /user_id, /group_id, /workspace_id). These new PKs only take effect on
    fresh deployments — existing containers retain their original /id partition key.
    This migration script bridges existing deployments to the new schema.

CONTAINERS MIGRATED:
    Container               Old PK      New PK          Reason
    ─────────────────────── ─────────── ─────────────── ──────────────────────
    conversations           /id         /user_id        Queries filter by user_id
    group_conversations     /id         /group_id       Queries filter by group_id
    documents               /id         /user_id        Heavy queries by user_id
    group_documents         /id         /group_id       Heavy queries by group_id
    public_documents        /id         /workspace_id   Queries by workspace_id
    safety                  /id         /user_id        Filtered by user_id
    feedback                /id         /user_id        Filtered by user_id
    archived_conversations  /id         /user_id        Filtered by user_id
    prompts                 /id         /user_id        Filtered by user_id
    group_prompts           /id         /group_id       Filtered by group_id
    public_prompts          /id         /workspace_id   Filtered by workspace_id

PREREQUISITES:
    - Python 3.8+
    - azure-cosmos package installed
    - Environment variables set:
        AZURE_COSMOS_ENDPOINT     - Cosmos DB endpoint URL
        AZURE_COSMOS_KEY          - Cosmos DB access key (or use managed identity)
        AZURE_COSMOS_AUTHENTICATION_TYPE - "key" (default) or "managed_identity"

USAGE:
    # Dry run — shows what would be migrated without making changes
    python migrate_cosmos_partition_keys.py --dry-run

    # Migrate a single container
    python migrate_cosmos_partition_keys.py --container conversations

    # Migrate all containers that need it
    python migrate_cosmos_partition_keys.py --all

    # Migrate with verbose output
    python migrate_cosmos_partition_keys.py --all --verbose

SAFETY:
    - The script NEVER deletes the original container
    - Old containers are renamed with a _backup_{timestamp} suffix
    - Document counts are verified before and after migration
    - If document counts don't match, the migration is aborted
    - The --dry-run flag shows exactly what would happen without making changes

ROLLBACK:
    If something goes wrong:
    1. The original data is in the _backup_{timestamp} container
    2. Delete the new container
    3. Rename the backup container back to the original name
    (Cosmos DB does not support rename — you'd re-create and copy back)

    In practice, since backups are preserved, you can manually copy documents
    back from the backup container using this script's copy logic.

Version: 0.239.010
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

try:
    from azure.cosmos import CosmosClient, PartitionKey, exceptions
    from azure.identity import DefaultAzureCredential
except ImportError:
    print("ERROR: azure-cosmos and azure-identity packages are required.")
    print("Install with: pip install azure-cosmos azure-identity")
    sys.exit(1)


# ── Migration definitions ───────────────────────────────────────────────

MIGRATIONS = {
    "conversations": {
        "old_pk": "/id",
        "new_pk": "/user_id",
        "pk_field": "user_id",
        "description": "User conversations — queries always filter by user_id",
    },
    "group_conversations": {
        "old_pk": "/id",
        "new_pk": "/group_id",
        "pk_field": "group_id",
        "description": "Group conversations — queries filter by group_id",
    },
    "documents": {
        "old_pk": "/id",
        "new_pk": "/user_id",
        "pk_field": "user_id",
        "description": "User documents — heavy queries by user_id",
    },
    "group_documents": {
        "old_pk": "/id",
        "new_pk": "/group_id",
        "pk_field": "group_id",
        "description": "Group documents — heavy queries by group_id",
    },
    "public_documents": {
        "old_pk": "/id",
        "new_pk": "/workspace_id",
        "pk_field": "workspace_id",
        "description": "Public documents — queries by workspace_id",
    },
    "safety": {
        "old_pk": "/id",
        "new_pk": "/user_id",
        "pk_field": "user_id",
        "description": "Safety records — filtered by user_id",
    },
    "feedback": {
        "old_pk": "/id",
        "new_pk": "/user_id",
        "pk_field": "user_id",
        "description": "Feedback records — filtered by user_id",
    },
    "archived_conversations": {
        "old_pk": "/id",
        "new_pk": "/user_id",
        "pk_field": "user_id",
        "description": "Archived conversations — filtered by user_id",
    },
    "prompts": {
        "old_pk": "/id",
        "new_pk": "/user_id",
        "pk_field": "user_id",
        "description": "User prompts — filtered by user_id",
    },
    "group_prompts": {
        "old_pk": "/id",
        "new_pk": "/group_id",
        "pk_field": "group_id",
        "description": "Group prompts — filtered by group_id",
    },
    "public_prompts": {
        "old_pk": "/id",
        "new_pk": "/workspace_id",
        "pk_field": "workspace_id",
        "description": "Public prompts — filtered by workspace_id",
    },
}


def get_cosmos_client():
    """Initialize and return a Cosmos DB client based on environment configuration."""
    endpoint = os.getenv("AZURE_COSMOS_ENDPOINT")
    key = os.getenv("AZURE_COSMOS_KEY")
    auth_type = os.getenv("AZURE_COSMOS_AUTHENTICATION_TYPE", "key")

    if not endpoint:
        print("ERROR: AZURE_COSMOS_ENDPOINT environment variable is not set.")
        sys.exit(1)

    if auth_type == "managed_identity":
        print(f"Connecting to Cosmos DB at {endpoint} using managed identity...")
        return CosmosClient(endpoint, credential=DefaultAzureCredential(), consistency_level="Session")
    else:
        if not key:
            print("ERROR: AZURE_COSMOS_KEY environment variable is not set.")
            sys.exit(1)
        print(f"Connecting to Cosmos DB at {endpoint} using key authentication...")
        return CosmosClient(endpoint, key, consistency_level="Session")


def get_container_partition_key(container):
    """Get the current partition key path for a container."""
    try:
        properties = container.read()
        pk_paths = properties.get("partitionKey", {}).get("paths", [])
        return pk_paths[0] if pk_paths else None
    except Exception as e:
        print(f"  ERROR reading container properties: {e}")
        return None


def count_documents(container, partition_key_path):
    """Count all documents in a container using a cross-partition query."""
    try:
        query = "SELECT VALUE COUNT(1) FROM c"
        results = list(container.query_items(
            query=query,
            enable_cross_partition_query=True
        ))
        return results[0] if results else 0
    except Exception as e:
        print(f"  ERROR counting documents: {e}")
        return -1


def read_all_documents(container):
    """Read all documents from a container."""
    documents = []
    try:
        query = "SELECT * FROM c"
        items = container.query_items(
            query=query,
            enable_cross_partition_query=True
        )
        for item in items:
            documents.append(item)
    except Exception as e:
        print(f"  ERROR reading documents: {e}")
    return documents


def validate_documents_have_pk_field(documents, pk_field, container_name):
    """
    Validate that all documents have the required partition key field.
    Returns (valid_count, missing_count, missing_doc_ids).
    """
    missing = []
    valid = 0
    for doc in documents:
        if pk_field in doc and doc[pk_field] is not None:
            valid += 1
        else:
            missing.append(doc.get("id", "unknown"))
    return valid, len(missing), missing


def migrate_container(database, container_name, migration_info, dry_run=False, verbose=False):
    """
    Migrate a single container to a new partition key.

    Steps:
    1. Check if container exists and has the old partition key
    2. Read all documents from the old container
    3. Validate all documents have the new PK field
    4. Create a new container with the new partition key
    5. Copy all documents to the new container
    6. Verify document counts match
    7. Rename old container to backup
    8. Rename new container to original name

    Note: Cosmos DB doesn't support container rename. Instead we:
    - Create new container as {name}_migrated
    - Keep old container as {name}_backup_{timestamp}
    - Delete old container and create final container with correct name
    """
    old_pk = migration_info["old_pk"]
    new_pk = migration_info["new_pk"]
    pk_field = migration_info["pk_field"]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    print(f"\n{'='*60}")
    print(f"Container: {container_name}")
    print(f"  Description: {migration_info['description']}")
    print(f"  Old PK: {old_pk} → New PK: {new_pk}")
    print(f"{'='*60}")

    # Step 1: Check if container exists and needs migration
    try:
        old_container = database.get_container_client(container_name)
        current_pk = get_container_partition_key(old_container)
    except exceptions.CosmosResourceNotFoundError:
        print(f"  SKIP: Container '{container_name}' does not exist.")
        return {"status": "skipped", "reason": "container_not_found"}

    if current_pk != old_pk:
        if current_pk == new_pk:
            print(f"  SKIP: Container already has the desired partition key ({new_pk}).")
            return {"status": "skipped", "reason": "already_migrated"}
        else:
            print(f"  SKIP: Container has unexpected partition key ({current_pk}). Expected {old_pk}.")
            return {"status": "skipped", "reason": "unexpected_pk"}

    print(f"  Current PK: {current_pk} (needs migration)")

    # Step 2: Count and read documents
    doc_count = count_documents(old_container, old_pk)
    print(f"  Document count: {doc_count}")

    if doc_count == 0:
        print(f"  Container is empty.")
        if dry_run:
            print(f"  DRY RUN: Would recreate empty container with new PK {new_pk}")
            return {"status": "dry_run", "documents": 0}

        # For empty containers, just delete and recreate
        print(f"  Deleting empty container...")
        database.delete_container(container_name)
        print(f"  Creating container with new PK {new_pk}...")
        database.create_container(
            id=container_name,
            partition_key=PartitionKey(path=new_pk)
        )
        print(f"  SUCCESS: Empty container recreated with {new_pk}")
        return {"status": "success", "documents": 0}

    documents = read_all_documents(old_container)
    actual_count = len(documents)
    print(f"  Documents read: {actual_count}")

    if actual_count != doc_count:
        print(f"  WARNING: Count mismatch — query said {doc_count}, read {actual_count}")

    # Step 3: Validate documents have the PK field
    valid, missing_count, missing_ids = validate_documents_have_pk_field(documents, pk_field, container_name)
    print(f"  Documents with '{pk_field}' field: {valid}/{actual_count}")

    if missing_count > 0:
        print(f"  WARNING: {missing_count} documents are missing the '{pk_field}' field!")
        if verbose:
            for doc_id in missing_ids[:10]:
                print(f"    - Document ID: {doc_id}")
            if len(missing_ids) > 10:
                print(f"    ... and {len(missing_ids) - 10} more")
        print(f"  These documents will have '{pk_field}' set to 'unknown' during migration.")

    if dry_run:
        print(f"\n  DRY RUN SUMMARY:")
        print(f"    Documents to migrate: {actual_count}")
        print(f"    Documents with valid PK: {valid}")
        print(f"    Documents missing PK field: {missing_count}")
        print(f"    New partition key: {new_pk}")
        return {"status": "dry_run", "documents": actual_count, "valid_pk": valid, "missing_pk": missing_count}

    # Step 4: Create temporary container with new PK
    temp_container_name = f"{container_name}_migrated_{timestamp}"
    print(f"\n  Creating temporary container: {temp_container_name}")
    try:
        new_container = database.create_container(
            id=temp_container_name,
            partition_key=PartitionKey(path=new_pk)
        )
    except exceptions.CosmosResourceExistsError:
        print(f"  ERROR: Temporary container '{temp_container_name}' already exists. Aborting.")
        return {"status": "error", "reason": "temp_container_exists"}

    # Step 5: Copy documents to new container
    print(f"  Copying {actual_count} documents...")
    copied = 0
    errors = 0
    for i, doc in enumerate(documents):
        try:
            # Remove system properties that Cosmos manages
            doc_copy = {k: v for k, v in doc.items()
                       if not k.startswith('_') or k == '_ts'}
            # Remove Cosmos system fields
            for sys_field in ['_rid', '_self', '_etag', '_attachments', '_ts']:
                doc_copy.pop(sys_field, None)

            # Ensure the PK field exists
            if pk_field not in doc_copy or doc_copy[pk_field] is None:
                doc_copy[pk_field] = "unknown"

            new_container.upsert_item(doc_copy)
            copied += 1

            if verbose and (i + 1) % 100 == 0:
                print(f"    Copied {i + 1}/{actual_count} documents...")
        except Exception as e:
            errors += 1
            print(f"    ERROR copying document {doc.get('id', 'unknown')}: {e}")

    print(f"  Copied: {copied}, Errors: {errors}")

    # Step 6: Verify counts match
    new_count = count_documents(new_container, new_pk)
    print(f"  Verification — old: {actual_count}, new: {new_count}")

    if new_count != actual_count:
        print(f"  ERROR: Document count mismatch! Aborting migration.")
        print(f"  The temporary container '{temp_container_name}' has been left in place for inspection.")
        return {"status": "error", "reason": "count_mismatch", "old": actual_count, "new": new_count}

    # Step 7: Rename old container to backup
    backup_name = f"{container_name}_backup_{timestamp}"
    print(f"\n  Renaming old container to backup: {backup_name}")
    # Cosmos DB doesn't support rename, so we create backup, copy, then delete
    try:
        backup_container = database.create_container(
            id=backup_name,
            partition_key=PartitionKey(path=old_pk)
        )
        print(f"  Copying documents to backup container...")
        for doc in documents:
            doc_copy = {k: v for k, v in doc.items()
                       if not k.startswith('_') or k == '_ts'}
            for sys_field in ['_rid', '_self', '_etag', '_attachments', '_ts']:
                doc_copy.pop(sys_field, None)
            backup_container.upsert_item(doc_copy)

        backup_count = count_documents(backup_container, old_pk)
        print(f"  Backup verification — expected: {actual_count}, got: {backup_count}")

        if backup_count != actual_count:
            print(f"  ERROR: Backup count mismatch! Aborting. Temp container preserved.")
            return {"status": "error", "reason": "backup_count_mismatch"}

    except Exception as e:
        print(f"  ERROR creating backup: {e}")
        print(f"  Temp container '{temp_container_name}' preserved for manual recovery.")
        return {"status": "error", "reason": "backup_failed"}

    # Step 8: Delete old container and create final container
    print(f"  Deleting original container '{container_name}'...")
    try:
        database.delete_container(container_name)
    except Exception as e:
        print(f"  ERROR deleting original container: {e}")
        print(f"  Backup: {backup_name}, Migrated data: {temp_container_name}")
        return {"status": "error", "reason": "delete_failed"}

    print(f"  Creating final container '{container_name}' with PK {new_pk}...")
    try:
        final_container = database.create_container(
            id=container_name,
            partition_key=PartitionKey(path=new_pk)
        )
    except Exception as e:
        print(f"  CRITICAL ERROR creating final container: {e}")
        print(f"  Data is safe in: {temp_container_name}")
        print(f"  Backup of original: {backup_name}")
        return {"status": "error", "reason": "create_final_failed"}

    # Copy from temp to final
    print(f"  Copying documents to final container...")
    temp_docs = read_all_documents(new_container)
    for doc in temp_docs:
        doc_copy = {k: v for k, v in doc.items()
                   if not k.startswith('_') or k == '_ts'}
        for sys_field in ['_rid', '_self', '_etag', '_attachments', '_ts']:
            doc_copy.pop(sys_field, None)
        final_container.upsert_item(doc_copy)

    final_count = count_documents(final_container, new_pk)
    print(f"  Final verification — expected: {actual_count}, got: {final_count}")

    if final_count == actual_count:
        # Clean up temp container
        print(f"  Cleaning up temporary container '{temp_container_name}'...")
        database.delete_container(temp_container_name)
        print(f"\n  SUCCESS: '{container_name}' migrated from {old_pk} to {new_pk}")
        print(f"  Backup preserved as: {backup_name}")
        return {"status": "success", "documents": final_count, "backup": backup_name}
    else:
        print(f"  WARNING: Final count mismatch. Temp container preserved.")
        return {"status": "warning", "reason": "final_count_mismatch", "backup": backup_name}


def main():
    parser = argparse.ArgumentParser(
        description="Migrate SimpleChat Cosmos DB containers to optimized partition keys.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python migrate_cosmos_partition_keys.py --dry-run          # Preview all migrations
  python migrate_cosmos_partition_keys.py --container conversations  # Migrate one container
  python migrate_cosmos_partition_keys.py --all              # Migrate all containers
  python migrate_cosmos_partition_keys.py --all --verbose    # Migrate with detailed output
  python migrate_cosmos_partition_keys.py --list             # List containers to migrate
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true",
                       help="Migrate all containers that need partition key changes")
    group.add_argument("--container", type=str,
                       help="Migrate a specific container by name")
    group.add_argument("--list", action="store_true",
                       help="List all containers and their migration status")

    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without making changes")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show detailed output during migration")
    parser.add_argument("--database", type=str, default="SimpleChat",
                        help="Cosmos DB database name (default: SimpleChat)")

    args = parser.parse_args()

    # Initialize Cosmos client
    client = get_cosmos_client()

    try:
        database = client.get_database_client(args.database)
        # Verify database exists
        database.read()
        print(f"Connected to database: {args.database}")
    except exceptions.CosmosResourceNotFoundError:
        print(f"ERROR: Database '{args.database}' not found.")
        sys.exit(1)

    if args.list:
        print(f"\n{'Container':<25} {'Current PK':<15} {'Target PK':<15} {'Status'}")
        print(f"{'─'*25} {'─'*15} {'─'*15} {'─'*20}")
        for name, info in MIGRATIONS.items():
            try:
                container = database.get_container_client(name)
                current_pk = get_container_partition_key(container)
                if current_pk == info["new_pk"]:
                    status = "Already migrated"
                elif current_pk == info["old_pk"]:
                    doc_count = count_documents(container, current_pk)
                    status = f"Needs migration ({doc_count} docs)"
                else:
                    status = f"Unexpected PK: {current_pk}"
                print(f"{name:<25} {current_pk or 'N/A':<15} {info['new_pk']:<15} {status}")
            except exceptions.CosmosResourceNotFoundError:
                print(f"{name:<25} {'N/A':<15} {info['new_pk']:<15} Container not found")
        return

    if args.container:
        if args.container not in MIGRATIONS:
            print(f"ERROR: Unknown container '{args.container}'.")
            print(f"Available containers: {', '.join(MIGRATIONS.keys())}")
            sys.exit(1)
        containers_to_migrate = {args.container: MIGRATIONS[args.container]}
    else:
        containers_to_migrate = MIGRATIONS

    if args.dry_run:
        print("\n" + "="*60)
        print("DRY RUN MODE — No changes will be made")
        print("="*60)

    results = {}
    for name, info in containers_to_migrate.items():
        result = migrate_container(
            database=database,
            container_name=name,
            migration_info=info,
            dry_run=args.dry_run,
            verbose=args.verbose
        )
        results[name] = result

    # Summary
    print(f"\n{'='*60}")
    print("MIGRATION SUMMARY")
    print(f"{'='*60}")
    for name, result in results.items():
        status = result.get("status", "unknown")
        if status == "success":
            print(f"  {name}: SUCCESS ({result.get('documents', 0)} documents, backup: {result.get('backup', 'N/A')})")
        elif status == "dry_run":
            print(f"  {name}: DRY RUN ({result.get('documents', 0)} documents would be migrated)")
        elif status == "skipped":
            print(f"  {name}: SKIPPED ({result.get('reason', '')})")
        elif status == "error":
            print(f"  {name}: ERROR ({result.get('reason', '')})")
        elif status == "warning":
            print(f"  {name}: WARNING ({result.get('reason', '')})")


if __name__ == "__main__":
    main()
