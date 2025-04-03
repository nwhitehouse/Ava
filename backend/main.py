from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import asyncio
from contextlib import asynccontextmanager

# Import the RAG chains (will initialize on import)
from rag_emails import rag_chain_global, homescreen_chain_global, client as weaviate_client

# Pydantic model for chat requests
class ChatRequest(BaseModel):
    message: str

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
    """Runs predefined RAG query to categorize emails for the homescreen."""
    if not homescreen_chain_global:
        raise HTTPException(status_code=503, detail="Homescreen RAG service not available")

    try:
        print("Invoking homescreen categorization chain...")
        # Input to this chain is currently ignored, prompt is fixed
        # LangChain RAG chains are often synchronous, run in thread pool
        result = await asyncio.to_thread(homescreen_chain_global.invoke, "Categorize emails for homescreen")
        print(f"Homescreen chain result: {result}")
        # The result should already be the parsed Pydantic object (dict)
        return result
    except Exception as e:
        print(f"Error invoking homescreen chain: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching homescreen email data: {str(e)}")

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