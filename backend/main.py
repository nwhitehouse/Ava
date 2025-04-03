from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import asyncio
from contextlib import asynccontextmanager
import weaviate.classes as wvc
import json
import time # For caching

# Import the RAG chains and Weaviate client
# Correctly import the global weaviate_client variable
from rag_emails import rag_chain_global, homescreen_chain_global, weaviate_client, WEAVIATE_CLASS_NAME, HomescreenData # Import the Pydantic model for caching type hint

# --- Caching Globals --- #
homescreen_cache: HomescreenData | None = None
last_cache_time: float = 0
CACHE_DURATION_SECONDS: int = 300 # Cache for 5 minutes

# Pydantic model for chat requests
class ChatRequest(BaseModel):
    message: str

# Pydantic model for single email response
class EmailDetails(BaseModel):
    id: str
    sender: str
    subject: str
    body: str
    received_date: str

# Pydantic model for email list item
class EmailListItem(BaseModel):
    id: str
    sender: str
    subject: str
    received_date: str

# Pydantic model for all emails response
class AllEmailsResponse(BaseModel):
    emails: list[EmailListItem]

# Async context manager for lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Application startup...")
    if not weaviate_client or not weaviate_client.is_connected():
        print("Weaviate client not connected on startup!")
        # Handle error appropriately - maybe prevent startup or log critical error
    if not rag_chain_global or not homescreen_chain_global:
        print("RAG chains not initialized on startup!")
        # Handle error appropriately
    yield
    # Shutdown
    print("Application shutdown...")
    if weaviate_client and weaviate_client.is_connected():
        weaviate_client.close()
        print("Weaviate connection closed.")

app = FastAPI(lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # Allow your frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Ava Backend"}

# --- RAG Email Chat Endpoint ---
@app.post("/api/email_rag")
async def email_rag_query(request: ChatRequest):
    """Receives a question, queries emails via RAG, returns text answer."""
    if not rag_chain_global:
        raise HTTPException(status_code=503, detail="RAG service not available")
    
    query = request.message
    if not query:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        print(f"Invoking RAG chain for query: {query}")
        # LangChain RAG chains are often synchronous, run in thread pool
        result = await asyncio.to_thread(rag_chain_global.invoke, query)
        print(f"RAG chain result: {result}")
        return {"answer": result.get('answer', "Sorry, I couldn't process that request.")}
    except Exception as e:
        print(f"Error invoking RAG chain: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing email query: {str(e)}")

# --- Homescreen Email Categorization Endpoint ---
@app.get("/api/homescreen_emails")
async def get_homescreen_emails():
    """Runs predefined RAG query to categorize emails for the homescreen, with caching."""
    global homescreen_cache, last_cache_time
    
    current_time = time.time()
    # Check cache validity
    if homescreen_cache and (current_time - last_cache_time < CACHE_DURATION_SECONDS):
        print("--- Returning CACHED homescreen data --- ")
        return homescreen_cache

    # Cache is invalid or empty, proceed with fetching
    print("--- Cache invalid or expired, fetching fresh homescreen data --- ")
    if not homescreen_chain_global:
        raise HTTPException(status_code=503, detail="Homescreen RAG service not available")

    try:
        print("Invoking homescreen categorization chain...")
        result_dict = await asyncio.to_thread(homescreen_chain_global.invoke, {})
        
        # --- DEBUG: Print the raw result from the chain --- #
        print("--- Homescreen Chain RAW Result --- ")
        try: print(json.dumps(result_dict, indent=2))
        except TypeError: print(result_dict)
        print("--- End Homescreen Chain RAW Result --- ")
        # --- END DEBUG --- #
        
        # Validate and store in cache (using Pydantic model for structure)
        try:
             homescreen_cache = HomescreenData(**result_dict) # Validate and convert
             last_cache_time = current_time
             print("--- Homescreen data cached successfully --- ")
        except Exception as pydantic_error:
             print(f"[ERROR] Pydantic validation failed for homescreen data: {pydantic_error}")
             # Optionally return stale cache if validation fails but cache exists
             # if homescreen_cache:
             #     print("[WARN] Returning stale cache due to validation error.")
             #     return homescreen_cache
             # Or raise error
             raise HTTPException(status_code=500, detail="Failed to process homescreen data structure.")

        return homescreen_cache # Return the newly cached & validated data
        
    except Exception as e:
        print(f"Error invoking homescreen chain: {e}")
        # Optionally return stale cache on error
        # if homescreen_cache:
        #     print("[WARN] Returning stale cache due to fetch error.")
        #     return homescreen_cache
        raise HTTPException(status_code=500, detail=f"Error fetching homescreen email data: {str(e)}")

# --- Get Single Email Details Endpoint ---
@app.get("/api/email/{email_id}", response_model=EmailDetails)
async def get_email_details(email_id: str):
    """Fetches the full details of a single email by its Weaviate UUID."""
    if not weaviate_client or not weaviate_client.is_connected():
        raise HTTPException(status_code=503, detail="Database service not available")

    try:
        print(f"Fetching email with ID: {email_id}")
        email_collection = weaviate_client.collections.get(WEAVIATE_CLASS_NAME)
        
        # Fetch the object by UUID
        email_object = email_collection.query.fetch_object_by_id(email_id)

        if email_object is None:
            raise HTTPException(status_code=404, detail="Email not found")

        print(f"Found email: {email_object.properties}")
        # Construct the response using the Pydantic model
        response_data = EmailDetails(
            id=str(email_object.uuid), # Use the actual uuid from the object
            sender=email_object.properties.get("sender", "N/A"),
            subject=email_object.properties.get("subject", "N/A"),
            body=email_object.properties.get("body", "N/A"),
            received_date=email_object.properties.get("received_date", "N/A")
        )
        return response_data

    except HTTPException as http_exc:
        # Re-raise HTTP exceptions (like 404)
        raise http_exc
    except Exception as e:
        print(f"Error fetching email details for ID {email_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching email details: {str(e)}")

# --- Get All Emails Endpoint ---
@app.get("/api/emails", response_model=AllEmailsResponse)
async def get_all_emails():
    """Fetches a list of all emails (basic details)."""
    if not weaviate_client or not weaviate_client.is_connected():
        raise HTTPException(status_code=503, detail="Database service not available")

    try:
        print("Fetching all emails...")
        email_collection = weaviate_client.collections.get(WEAVIATE_CLASS_NAME)

        # Fetch objects - retrieve only necessary props + UUID
        # UUID should be returned by default in obj.uuid
        response = email_collection.query.fetch_objects(
            limit=100, # Add a reasonable limit
            return_properties=["sender", "subject", "received_date"]
        )

        email_list = []
        for obj in response.objects:
            email_list.append(
                EmailListItem(
                    id=str(obj.uuid),
                    sender=obj.properties.get("sender", "N/A"),
                    subject=obj.properties.get("subject", "N/A"),
                    received_date=obj.properties.get("received_date", "N/A")
                )
            )

        print(f"Returning {len(email_list)} emails.")
        return AllEmailsResponse(emails=email_list)

    except Exception as e:
        print(f"Error fetching all emails: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching email list: {str(e)}")

# --- Original Streaming Chat Endpoint (Commented out for now) ---
# from sse_starlette.sse import EventSourceResponse
# from openai import OpenAI

# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# async def stream_openai_response(message: str):
#     # ... (original streaming logic)
#     pass

# @app.get("/api/chat")
# async def chat_endpoint(message: str):
#     # ... (original endpoint logic)
#     return EventSourceResponse(stream_openai_response(message))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3001) 