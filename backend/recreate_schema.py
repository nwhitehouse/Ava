# backend/recreate_schema.py
import os
import sys
import weaviate
import weaviate.classes as wvc
from dotenv import load_dotenv

# Load environment variables (assuming WEAVIATE_URL, WEAVIATE_API_KEY are set)
# Ensure OPENAI_API_KEY is also available if required by your Weaviate setup/WCS
load_dotenv()

WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080") # Default to localhost if not set
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") 
WEAVIATE_CLASS_NAME = "Email" # Make sure this matches the name used elsewhere

print(f"--- Schema Recreation Script for Collection: '{WEAVIATE_CLASS_NAME}' ---")
print(f"Target Weaviate URL: {WEAVIATE_URL}")

# --- Main Logic --- 
if __name__ == "__main__":

    # --- Safety Check --- #
    print("\n!!! WARNING !!!")
    print(f"This script will first ATTEMPT TO DELETE the Weaviate collection named '{WEAVIATE_CLASS_NAME}'.")
    print("This will PERMANENTLY REMOVE all data within that collection.")
    print("It will then attempt to RECREATE the collection with automatic OpenAI vectorization.")
    confirm = input(f"Type 'DELETE AND RECREATE {WEAVIATE_CLASS_NAME}' to confirm: ")

    if confirm != f"DELETE AND RECREATE {WEAVIATE_CLASS_NAME}":
        print("Confirmation failed. Aborting operation.")
        exit(1)
    # --- End Safety Check --- #

    client = None # Initialize client to None for finally block
    try:
        print("\nConnecting to Weaviate...")
        # Choose connection method based on your setup (WCS, local, custom)
        if WEAVIATE_URL.startswith("https://") and ".weaviate.network" in WEAVIATE_URL: 
             print("Attempting WCS connection...")
             if not WEAVIATE_API_KEY:
                 print("Error: WEAVIATE_API_KEY is required for WCS connection.", file=sys.stderr)
                 exit(1)
             client = weaviate.connect_to_wcs(
                 cluster_url=WEAVIATE_URL,
                 auth_credentials=weaviate.auth.AuthApiKey(WEAVIATE_API_KEY),
                 headers={
                     "X-OpenAI-Api-Key": OPENAI_API_KEY 
                 } if OPENAI_API_KEY else {}
             )
        elif WEAVIATE_URL == "http://localhost:8080":
             print("Attempting local connection...")
             client = weaviate.connect_to_local(
                 headers={
                     "X-OpenAI-Api-Key": OPENAI_API_KEY 
                 } if OPENAI_API_KEY else {}
             )
        else:
             # Add custom connection logic if needed based on URL
             print(f"Attempting custom connection to {WEAVIATE_URL}...")
             # Example: Adjust ports if necessary
             # client = weaviate.connect_to_custom(...) 
             raise NotImplementedError("Custom connection logic not implemented for this URL.")

        client.is_ready() # Check connection
        print("Connected successfully.")

        # 1. Delete existing collection if it exists
        if client.collections.exists(WEAVIATE_CLASS_NAME):
            print(f"Attempting to delete existing collection '{WEAVIATE_CLASS_NAME}'...")
            try:
                client.collections.delete(WEAVIATE_CLASS_NAME)
                print(f"Collection '{WEAVIATE_CLASS_NAME}' deleted successfully.")
            except Exception as del_e:
                 print(f"Error deleting collection: {del_e}. Attempting to continue with creation...")
                 # Decide if you want to proceed or exit on deletion error
                 # exit(1) 
        else:
            print(f"Collection '{WEAVIATE_CLASS_NAME}' does not exist, no need to delete.")

        # 2. Create the collection with the correct schema
        print(f"Creating collection '{WEAVIATE_CLASS_NAME}' with text2vec-openai vectorizer...")
        client.collections.create(
            name=WEAVIATE_CLASS_NAME,
            properties=[
                # Not vectorizing sender or date by default
                wvc.config.Property(name="sender", data_type=wvc.config.DataType.TEXT, skip_vectorization=True),
                wvc.config.Property(name="received_date", data_type=wvc.config.DataType.TEXT, skip_vectorization=True),
                # Vectorizing subject and body
                wvc.config.Property(name="subject", data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="body", data_type=wvc.config.DataType.TEXT),
            ],
            # Configure the OpenAI vectorizer
            vectorizer_config=wvc.config.Configure.Vectorizer.text2vec_openai(
                model="text-embedding-3-small", # Specify your desired model
                type_="text" # Use type_ instead of type
            )
            # Optional: Add vector index config if needed
            # vector_index_config=wvc.config.Configure.VectorIndex.hnsw(...)
        )
        print(f"Collection '{WEAVIATE_CLASS_NAME}' created successfully with automatic vectorization enabled for subject and body.")

    except Exception as e:
        print(f"\n--- An error occurred during schema recreation --- ", file=sys.stderr)
        print(f"Error type: {type(e).__name__}", file=sys.stderr)
        print(f"Error details: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        print("----------------------------------------------------\n", file=sys.stderr)
        exit(1)
    finally:
        if client and client.is_connected():
            client.close()
            print("\nWeaviate connection closed.")

    print("\nSchema recreation script finished.") 