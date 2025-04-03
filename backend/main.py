from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import asyncio
from contextlib import asynccontextmanager
import weaviate.classes as wvc
import json
import time # For caching
from datetime import datetime, timezone
import re # Import regex for parsing
from pathlib import Path # For handling file path
from typing import List # For list type hinting

# Import settings utilities
from settings_utils import load_settings, save_settings, UserSettings

# Import the RAG chains and Weaviate client
# Correctly import the global weaviate_client variable
from rag_emails import (
    rag_chain_global, 
    homescreen_chain_global, 
    weaviate_client, 
    WEAVIATE_CLASS_NAME,
    HomescreenData,
    ChatRagResponse, # Response model for chat
    EmailRef, # Model for references
    llm as llm_global
)

# --- Caching Globals --- #
homescreen_cache: HomescreenData | None = None
last_cache_time: float = 0
CACHE_DURATION_SECONDS: int = 300 # Cache for 5 minutes

# --- Configuration --- #
# SETTINGS_FILE constant moved to settings_utils.py

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

# Removed IngestEmailRequest
# Pydantic model for bulk email ingestion
class BulkIngestRequest(BaseModel):
    raw_text: str

# Pydantic model for summarize request
class SummarizeRequest(BaseModel):
    questions: List[str]

# --- Utility Functions for Parsing --- #
def parse_bulk_emails(raw_text: str) -> list[dict]:
    """Parses raw text containing multiple emails into a list of dicts,
       expecting separation by # Email [number] and markdown headers.
    """
    emails = []
    # Split emails based on the specific pattern "# Email \d+"
    email_chunks = re.split(r'^# Email \d+\s*$\n', raw_text.strip(), flags=re.MULTILINE)
    
    email_chunks = [chunk.strip() for chunk in email_chunks if chunk.strip()] # Remove empty leading/trailing chunks

    print(f"--- Found {len(email_chunks)} potential email chunks after splitting by '# Email ...' ---")

    for i, chunk in enumerate(email_chunks):
        email_data = {
            "sender": "Unknown Sender",
            "subject": "No Subject",
            "body": chunk, # Default body is the whole chunk initially
            "received_date": datetime.now(timezone.utc).isoformat() # Default date
        }

        lines = chunk.split('\n')
        body_start_line_index = 0
        headers_parsed_count = 0 # Count how many headers we found for better body detection

        for idx, line in enumerate(lines):
            line_strip = line.strip()
            line_lower = line_strip.lower()
            match_found = False

            # Look for markdown bold headers
            if line_lower.startswith('**from:**'):
                # Extract content after **From:**, removing potential trailing **
                sender_raw = line_strip[len('**From:**'):].strip()
                if sender_raw.endswith('**'): sender_raw = sender_raw[:-2].strip()
                email_data["sender"] = sender_raw
                match_found = True
            elif line_lower.startswith('**to:**'): # Ignore To
                match_found = True
                pass
            elif line_lower.startswith('**subject:**'):
                subject_raw = line_strip[len('**Subject:**'):].strip()
                if subject_raw.endswith('**'): subject_raw = subject_raw[:-2].strip()
                email_data["subject"] = subject_raw
                match_found = True
            elif line_lower.startswith('**date:**'):
                date_raw = line_strip[len('**Date:**'):].strip()
                if date_raw.endswith('**'): date_raw = date_raw[:-2].strip()
                email_data["received_date"] = date_raw # Store raw date string
                match_found = True

            if match_found:
                headers_parsed_count += 1
                body_start_line_index = idx + 1 # Potential body starts after this line
            elif headers_parsed_count > 0 and not line.strip():
                # If we've found at least one header and hit a blank line, 
                # assume body starts definitively after this blank line.
                body_start_line_index = idx + 1
                break # Stop header scanning
            elif headers_parsed_count == 0 and idx > 5: 
                 # If we haven't found any headers after several lines, assume it's all body
                 body_start_line_index = 0
                 break
            elif headers_parsed_count > 0 and idx >= body_start_line_index : 
                # If we have found headers, and this line is not blank and not a header 
                # then the body must have started at body_start_line_index, stop scanning
                break

        # Extract the body based on where headers likely ended
        body_lines = lines[body_start_line_index:]
        email_data["body"] = '\n'.join(body_lines).strip()

        # Add only if we have a plausible body
        if email_data["body"]:
            emails.append(email_data)
            print(f"  Parsed Email Chunk {i+1}: Sender='{email_data['sender']}', Subject='{email_data['subject'][:30]}...', Date='{email_data['received_date']}'")
        else:
             print(f"  Skipped Email Chunk {i+1}: Could not extract a valid body after headers (or no headers found).")

    return emails

# --- Utility Functions for Settings --- #
# load_settings and save_settings moved to settings_utils.py

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

# --- RAG Email Chat Endpoint (Simpler - Link All Retrieved) ---
@app.post("/api/email_rag", response_model=ChatRagResponse)
async def email_rag_query(request: ChatRequest):
    """Runs RAG to get answer and links all retrieved emails as references."""
    if not rag_chain_global:
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
        # formatted_context = rag_result.get("formatted_context", "") # No longer needed here
        
        print(f"Primary RAG answer text: {answer_text}")
        print(f"Primary RAG retrieved {len(retrieved_objects)} objects")

        # --- Step 2: Build final references directly from ALL retrieved objects --- #
        # Reverted: Removed heuristic check
        references_list: list[EmailRef] = []
        print(f"--- Building references from all {len(retrieved_objects)} retrieved objects --- ")
        
        for obj in retrieved_objects:
            obj_id = str(obj.uuid)
            properties = obj.properties
            subject = properties.get("subject", "No Subject")
            # sender = properties.get("sender", "") # No longer needed for check
            
            # subject_lower = subject.lower() # No longer needed for check
            # sender_lower = sender.lower() # No longer needed for check
            
            # Always add reference if object was retrieved
            references_list.append(EmailRef(id=obj_id, subject=subject))
            print(f"[Reference Added] ID: {obj_id}, Subject: {subject}")

        # Construct final response
        final_response = ChatRagResponse(
            answer_text=answer_text or "Sorry, I couldn't generate a response.", 
            references=references_list
        )
        
        print(f"Final structured response (linking all retrieved): {final_response}")
        return final_response 
        
    except Exception as e:
        print(f"Error invoking/processing RAG chain: {e}")
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

# --- Delete Single Email Endpoint ---
@app.delete("/api/email/{email_id}")
async def delete_single_email(email_id: str):
    """Deletes a single email by its Weaviate UUID."""
    if not weaviate_client or not weaviate_client.is_connected():
        raise HTTPException(status_code=503, detail="Database service not available")

    try:
        print(f"--- Attempting to DELETE email with ID: {email_id} ---")
        email_collection = weaviate_client.collections.get(WEAVIATE_CLASS_NAME)
        
        # Attempt to delete the object by UUID
        # The `delete_object_by_id` method doesn't typically raise an error if the ID doesn't exist,
        # it just does nothing. We can optionally check existence first if needed.
        email_collection.data.delete_by_id(uuid=email_id)
        
        # We can't easily confirm deletion without querying again, so assume success if no error
        print(f"Successfully requested deletion for email ID: {email_id} (if it existed).")
        
        return {"message": f"Email with ID {email_id} deleted successfully (if it existed)."}

    except Exception as e:
        import traceback
        print(f"[ERROR] Failed to delete email ID {email_id}: {e}")
        traceback.print_exc()
        # Return 500 for unexpected errors during deletion attempt
        raise HTTPException(status_code=500, detail=f"Failed to delete email: {str(e)}")

# --- Ingest Bulk Emails Endpoint --- 
@app.post("/api/ingest_bulk_emails")
async def ingest_bulk_emails(request: BulkIngestRequest):
    """Receives raw text, parses it into emails, and ingests them into Weaviate."""
    if not weaviate_client or not weaviate_client.is_connected():
        raise HTTPException(status_code=503, detail="Database service not available")

    if not request.raw_text.strip():
        raise HTTPException(status_code=400, detail="Raw text cannot be empty")

    try:
        print(f"--- Received bulk text for ingestion (length: {len(request.raw_text)}) ---")
        
        # Parse the raw text into individual email data dictionaries
        parsed_emails = parse_bulk_emails(request.raw_text)
        
        if not parsed_emails:
            return {"message": "No valid emails found to ingest in the provided text.", "count": 0}

        print(f"--- Attempting to ingest {len(parsed_emails)} parsed emails via insert_many --- ")
        email_collection = weaviate_client.collections.get(WEAVIATE_CLASS_NAME)
        
        # Use insert_many for efficiency
        result = email_collection.data.insert_many(parsed_emails)
        
        ingested_count = len(result.uuids)
        error_count = 0
        if hasattr(result, 'errors') and result.errors:
            error_count = len(result.errors)
            print(f"[WARN] Encountered {error_count} errors during bulk ingestion.")
        elif hasattr(result, 'has_errors') and result.has_errors:
             print("[WARN] Some unspecified errors occurred during ingestion.")
             error_count = len(parsed_emails) - ingested_count # Estimate error count

        final_message = f"Ingestion complete. Successfully ingested: {ingested_count}. Failed: {error_count}."
        print(f"--- {final_message} --- ")
        
        return {"message": final_message, "count": ingested_count}

    except Exception as e:
        import traceback
        print(f"[ERROR] Failed during bulk email ingestion process: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to ingest emails: {str(e)}")

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

# --- Settings Endpoints --- #
@app.get("/api/settings", response_model=UserSettings)
async def get_settings():
    """Retrieves the current user settings."""
    print("--- GET /api/settings called ---")
    # Load settings using the utility function from settings_utils
    settings = await asyncio.to_thread(load_settings)
    return settings

@app.post("/api/settings")
async def update_settings(settings: UserSettings): # Request body is parsed into UserSettings model
    """Updates and saves the user settings."""
    print(f"--- POST /api/settings called with data: {settings} ---")
    try:
        # Save settings using the utility function from settings_utils
        await asyncio.to_thread(save_settings, settings)
        return {"message": "Settings updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {str(e)}")

# --- Summarize Chat Questions Endpoint --- #
@app.post("/api/summarize_questions")
async def summarize_questions(request: SummarizeRequest):
    """Uses an LLM to summarize key topics from a list of user questions."""
    if not request.questions:
        return {"summary": "No questions provided to summarize."}

    # Use the globally initialized LLM (ensure it's available)
    # NOTE: Consider error handling if llm_global isn't initialized
    # This reuses the LLM instance from rag_emails.py initialization
    if not llm_global:
         raise HTTPException(status_code=503, detail="LLM service not available")

    print(f"--- POST /api/summarize_questions called with {len(request.questions)} questions ---")
    
    # Format questions for the prompt
    formatted_questions = "\n".join([f"- {q}" for q in request.questions])
    
    prompt_template = f"""You are an assistant that analyzes user questions to identify recurring themes and important topics.
    Based *only* on the list of user questions below, identify the key topics, keywords, project names, or people mentioned frequently.
    Focus on what the user seems to care most about or asks about repeatedly.
    Provide a concise summary (1-2 sentences, maybe a few bullet points) suitable for helping the user define what is important to them regarding their emails.

    User Questions:
    {formatted_questions}

    Concise Summary:
    """
    prompt = ChatPromptTemplate.from_template(prompt_template)
    
    # Create a simple chain: prompt -> LLM -> string output
    summarize_chain = prompt | llm_global | StrOutputParser()
    
    try:
        # Invoke the chain asynchronously
        summary = await summarize_chain.ainvoke({}) # Pass empty dict as input to trigger chain
        print(f"--- Generated Summary: {summary} ---")
        return {"summary": summary}
        
    except Exception as e:
        print(f"[ERROR] Failed to summarize questions: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")

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