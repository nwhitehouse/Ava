# backend/delete_all_emails.py
import os
import sys
import weaviate.classes as wvc # Import Weaviate classes needed for filter

# Attempt to import the configured Weaviate client and class name
try:
    # Ensure backend directory is in path if running from workspace root,
    # or run this script directly from the backend directory.
    from rag_emails import weaviate_client, WEAVIATE_CLASS_NAME
except ImportError as e:
    print(f"Error importing Weaviate client/config from rag_emails: {e}", file=sys.stderr)
    print("Please ensure this script is run from the 'backend' directory or that the backend directory is in your PYTHONPATH.", file=sys.stderr)
    exit(1)

# --- Deletion Logic ---
if __name__ == "__main__":
    print("--- WARNING ---")
    print(f"This script will attempt to DELETE ALL objects from the Weaviate collection: '{WEAVIATE_CLASS_NAME}'")
    print("This action is irreversible.")
    confirm = input("Type 'DELETE ALL' to confirm: ")

    if confirm != "DELETE ALL":
        print("Confirmation failed. Aborting deletion.")
        exit(1)

    if not weaviate_client or not weaviate_client.is_connected():
        print("Error: Weaviate client is not available or not connected.", file=sys.stderr)
        exit(1)

    print(f"\nProceeding with deletion from '{WEAVIATE_CLASS_NAME}'...")

    try:
        email_collection = weaviate_client.collections.get(WEAVIATE_CLASS_NAME)

        # --- New Strategy: Fetch all UUIDs and delete one by one --- 
        print("Fetching all object UUIDs...")
        # Use iterator for potentially large collections. 
        # Fetch default metadata which includes UUID.
        uuids_to_delete = []
        for obj in email_collection.iterator(): # Removed return_metadata
            # Access UUID via obj.uuid (direct access)
            if hasattr(obj, 'uuid') and obj.uuid is not None:
                 uuids_to_delete.append(obj.uuid)
            else:
                 # Check if maybe properties has it? Unlikely but worth logging
                 props_uuid = obj.properties.get('id') or obj.properties.get('uuid') if hasattr(obj, 'properties') else None
                 if props_uuid:
                     uuids_to_delete.append(props_uuid)
                     print(f"[WARN] Found UUID in properties for object: {obj}")
                 else:
                     print(f"[WARN] Found object without UUID: {obj}") # Should not happen

        if not uuids_to_delete:
            print("No objects found in the collection. Nothing to delete.")
        else:
            print(f"Found {len(uuids_to_delete)} objects. Proceeding with deletion by ID...")
            deleted_count = 0
            failed_count = 0
            # Delete one by one (less efficient than batch, but avoids filter issues)
            for i, uuid_to_delete in enumerate(uuids_to_delete):
                try:
                    email_collection.data.delete_by_id(uuid=uuid_to_delete)
                    deleted_count += 1
                    if (i + 1) % 50 == 0: # Log progress every 50 deletions
                         print(f"  Deleted {deleted_count}/{len(uuids_to_delete)}...")
                except Exception as del_err:
                    print(f"  Error deleting object with UUID {uuid_to_delete}: {del_err}")
                    failed_count += 1
            
            print("\n--- Deletion Summary ---")
            print(f"Objects targeted for deletion: {len(uuids_to_delete)}")
            print(f"Objects successfully deleted: {deleted_count}")
            print(f"Objects failed to delete: {failed_count}")
            print("----------------------\n")

            if failed_count > 0:
                print("[WARN] Some objects failed to delete. Check errors above.", file=sys.stderr)
                exit(1) # Exit with error code if any deletion failed

    except Exception as e:
        import traceback
        print(f"\n--- An error occurred during the deletion process ---", file=sys.stderr)
        print(f"Error type: {type(e).__name__}", file=sys.stderr)
        print(f"Error details: {e}", file=sys.stderr)
        print("Traceback:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        print("----------------------------------------------------\n", file=sys.stderr)
        exit(1)
    finally:
        # Let main app manage client lifecycle
        print("Deletion script finished.") 