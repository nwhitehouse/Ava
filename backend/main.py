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
from rag_emails import (
    rag_chain_global, 
    homescreen_chain_global, 
    relevance_check_chain_global, # Import the new chain
    weaviate_client, 
    WEAVIATE_CLASS_NAME,
    HomescreenData,
    ChatRagResponse, # Response model for chat
    EmailRef # Model for references
)

# --- Caching Globals --- #
homescreen_cache: HomescreenData | None = None
last_cache_time: float = 0
CACHE_DURATION_SECONDS: int = 300 # Cache for 5 minutes

# --- Pydantic Models --- #

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

# Define EmailRef BEFORE ChatRagResponse
class EmailRef(BaseModel):
    id: str
    subject: str

# Pydantic model for ChatRagResponse
class ChatRagResponse(BaseModel):
    answer_text: str
    references: list[EmailRef]

# Async context manager for lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Application startup...")
    if not weaviate_client or not weaviate_client.is_connected():
        print("Weaviate client not connected on startup!")
        # Handle error appropriately - maybe prevent startup or log critical error
    if not rag_chain_global or not homescreen_chain_global or not relevance_check_chain_global:
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

# --- RAG Email Chat Endpoint (Two-LLM Call for References) ---
@app.post("/api/email_rag", response_model=ChatRagResponse)
async def email_rag_query(request: ChatRequest):
    """Runs RAG to get answer, then checks relevance for references."""
    if not rag_chain_global or not relevance_check_chain_global:
        raise HTTPException(status_code=503, detail="RAG service not available")
    query = request.message
    if not query:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    try:
        # --- Step 1: Invoke primary RAG chain --- 
        print(f"Invoking primary RAG chain for query: {query}")
        input_dict = {"question": query}
        # Expects: {"retrieved_objects": [...], "formatted_context": "...", "answer_text": "..."}
        rag_result = await asyncio.to_thread(rag_chain_global.invoke, input_dict)
        
        answer_text = rag_result.get("answer_text", "")
        retrieved_objects = rag_result.get("retrieved_objects", [])
        formatted_context = rag_result.get("formatted_context", "") # Get context for relevance check
        
        print(f"Primary RAG answer text: {answer_text}")
        print(f"Primary RAG retrieved {len(retrieved_objects)} objects")

        # --- Step 2: Invoke Relevance Check Chain --- #
        relevant_ids = []
        if answer_text and formatted_context and retrieved_objects: # Only run if we have ingredients
            try:
                print("--- Invoking Relevance Check Chain --- ")
                relevance_input = {"answer_text": answer_text, "formatted_context": formatted_context}
                # Expects: {"ids": [...]} 
                relevance_result = await asyncio.to_thread(relevance_check_chain_global.invoke, relevance_input)
                relevant_ids = relevance_result.get('ids', [])
                print(f"Relevance Check found IDs: {relevant_ids}")
            except Exception as relevance_exc:
                # Log error but don't fail the whole request, just return no references
                print(f"[ERROR] Relevance check chain failed: {relevance_exc}")
                relevant_ids = [] # Default to empty list on error
        else:
             print("Skipping relevance check (missing answer, context, or objects).")

        # --- Step 3: Build final references based on relevance check --- #
        references_list: list[EmailRef] = []
        object_map = {str(obj.uuid): obj for obj in retrieved_objects} # Map IDs to objects for easy lookup
        
        for rel_id in relevant_ids:
            if rel_id in object_map:
                 obj = object_map[rel_id]
                 subject = obj.properties.get("subject", "No Subject")
                 references_list.append(EmailRef(id=rel_id, subject=subject))
                 print(f"[Final Reference Added] ID: {rel_id}, Subject: {subject}")
            else:
                 print(f"[WARN] Relevant ID {rel_id} not found in originally retrieved objects.")

        # Construct final response
        final_response = ChatRagResponse(
            answer_text=answer_text or "Sorry, I couldn't generate a response.", 
            references=references_list
        )
        
        print(f"Final structured response with relevance check: {final_response}")
        return final_response 
        
    except Exception as e:
        print(f"Error invoking/processing RAG chains: {e}")
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
        
        # Fetch the object by UUID, specifying properties to return
        email_object = email_collection.query.fetch_object_by_id(
            uuid=email_id,
            return_properties=["sender", "subject", "body", "received_date"] 
        )

        if email_object is None:
            raise HTTPException(status_code=404, detail="Email not found")

        print(f"Found email properties: {email_object.properties}") # Log fetched props
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