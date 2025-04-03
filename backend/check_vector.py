# backend/check_vector.py
import os
import sys
import argparse # For command-line arguments

# Attempt to import the configured Weaviate client and class name
try:
    from rag_emails import weaviate_client, WEAVIATE_CLASS_NAME
except ImportError as e:
    print(f"Error importing Weaviate client/config from rag_emails: {e}", file=sys.stderr)
    print("Please ensure this script is run from the 'backend' directory or that the backend directory is in your PYTHONPATH.", file=sys.stderr)
    exit(1)

# --- Check Vector Logic --- 
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check if a Weaviate object has a vector.")
    parser.add_argument("uuid", help="The UUID of the object to check.")
    args = parser.parse_args()
    
    target_uuid = args.uuid

    if not weaviate_client or not weaviate_client.is_connected():
        print("Error: Weaviate client is not available or not connected.", file=sys.stderr)
        exit(1)

    print(f"Checking for vector on object with UUID: {target_uuid} in collection '{WEAVIATE_CLASS_NAME}'...")

    try:
        email_collection = weaviate_client.collections.get(WEAVIATE_CLASS_NAME)
        
        # Fetch the object by ID, explicitly requesting the vector
        obj = email_collection.query.fetch_object_by_id(
            uuid=target_uuid,
            include_vector=True
        )

        if obj is None:
            print(f"Result: Object with UUID {target_uuid} NOT FOUND.")
        elif obj.vector is not None:
            # Check if the vector dict is non-empty (or adjust based on actual vector format)
            if isinstance(obj.vector, dict) and len(obj.vector) > 0:
                 print(f"Result: Object FOUND and HAS a vector (vector keys: {list(obj.vector.keys())}).")
            elif isinstance(obj.vector, list) and len(obj.vector) > 0:
                 print(f"Result: Object FOUND and HAS a vector (vector length: {len(obj.vector)})." )
            else:
                 print(f"Result: Object FOUND but vector attribute is present but seems EMPTY or invalid ({obj.vector}).")
        else:
            print(f"Result: Object FOUND but does NOT have a vector (vector attribute is None).")
            print("       This likely means vectorization failed or was skipped during ingestion.")

    except Exception as e:
        import traceback
        print(f"\n--- An error occurred during the check --- ", file=sys.stderr)
        print(f"Error type: {type(e).__name__}", file=sys.stderr)
        print(f"Error details: {e}", file=sys.stderr)
        print("Traceback:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        print("------------------------------------------\n", file=sys.stderr)
        exit(1)
    finally:
        # Let main app manage client lifecycle
        print("Check script finished.") 