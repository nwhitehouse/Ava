import os
import weaviate
import weaviate.classes as wvc # Keep this import for fetch_objects
from dotenv import load_dotenv
from operator import itemgetter
import traceback # Import traceback for use in the except block

# LangChain imports
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_weaviate.vectorstores import WeaviateVectorStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableParallel, RunnableLambda, RunnableConfig
from langchain_core.documents import Document # For type hinting
from pydantic import BaseModel, Field # For structured output

# Import settings utilities from the new file
from settings_utils import load_settings, UserSettings 

# Load environment variables (from backend/.env or .env)
load_dotenv()

# --- Configuration ---
WEAVIATE_URL = "http://localhost:8080"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_CHAT_MODEL = "gpt-4o-mini"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
WEAVIATE_CLASS_NAME = "Email"
HOMESCREEN_EMAIL_LIMIT = 20 # How many emails to fetch for homescreen context

# Check for API Key
if not OPENAI_API_KEY:
    print("ERROR: OPENAI_API_KEY environment variable not set.")
    exit(1)

# --- Pydantic Models for Structured Output ---
class EmailInfo(BaseModel):
    id: str = Field(description="The unique ID (UUID) of the email from the context")
    heading: str = Field(description="A very short (3-7 words) AI-generated heading summarizing the email's key point or action.")
    subject: str = Field(description="The original subject line of the email")
    sender: str = Field(description="The sender of the email")
    reasoning: str = Field(description="Brief reason why this email fits the category")

class HomescreenData(BaseModel):
    urgent: list[EmailInfo] = Field(description="List of emails needing urgent response from me", default=[])
    delegate: list[EmailInfo] = Field(description="List of emails that can potentially be delegated", default=[])
    waiting_on: list[EmailInfo] = Field(description="List of emails where I am waiting for information from someone else", default=[])

# -- Models for Structured Chat RAG Response -- #
class EmailRef(BaseModel):
    id: str = Field(description="The unique ID (UUID) of the referenced email.")
    subject: str = Field(description="The subject of the referenced email.")

class ChatRagResponse(BaseModel):
    answer_text: str = Field(description="The textual answer to the user's question.")
    references: list[EmailRef] = Field(description="List of emails explicitly mentioned or summarized in the answer.", default=[])

# -- Model for Relevance Check LLM Output -- #
class RelevantIDs(BaseModel):
    ids: list[str] = Field(description="A list of email UUIDs deemed relevant to the answer text.")

# --- Global Weaviate Client & Embeddings --- 
weaviate_client: weaviate.WeaviateClient | None = None
embeddings: OpenAIEmbeddings | None = None # Make embeddings global

# --- Helper Functions ---

def format_weaviate_objects_for_llm(objects) -> str:
    """Formats native Weaviate objects for LLM context, ensuring UUID is included."""
    formatted_list = []
    print("--- Formatting Weaviate Objects for LLM Context ---") # DEBUG
    for i, obj in enumerate(objects):
        email_uuid = str(obj.uuid)
        print(f"[DEBUG] Object {i+1} UUID: {email_uuid}") # DEBUG
        properties = obj.properties
        entry = (
            f"Email {i+1} (ID: {email_uuid}):\n" + 
            f"  Sender: {properties.get('sender', 'N/A')}\n" +
            f"  Subject: {properties.get('subject', 'N/A')}\n" +
            f"  Date: {properties.get('received_date', 'N/A')}\n" +
            f"  Body: {properties.get('body', 'N/A')}"
        )
        formatted_list.append(entry)
    print("--- Finished Formatting Weaviate Objects ---") # DEBUG
    return "\n---\n".join(formatted_list)

# --- RAG Chain Definitions ---

def embed_query(query: str) -> list[float]:
    """Embeds the user query using the global embeddings model."""
    if not embeddings:
         print("[ERROR] Embeddings model not initialized.")
         return []
    try:
        print(f"--- Embedding query: {query[:50]}... ---")
        embedding = embeddings.embed_query(query)
        print(f"--- Embedding generated (dim: {len(embedding)}) ---")
        return embedding
    except Exception as e:
        print(f"[ERROR] Query embedding failed: {e}")
        return []

def fetch_emails_by_vector(embedding: list[float]) -> list:
    """Fetches emails using native Weaviate vector search."""
    if not weaviate_client or not weaviate_client.is_connected() or not embedding:
        print("[ERROR] Native vector search failed: Client not connected or no embedding.")
        return []
    try:
        print(f"--- Fetching emails via native vector search (limit 5) ---")
        email_collection = weaviate_client.collections.get(WEAVIATE_CLASS_NAME)
        response = email_collection.query.near_vector(
            near_vector=embedding,
            limit=5,
            return_properties=["sender", "subject", "received_date", "body"]
            # UUID included on obj.uuid by default
        )
        print(f"--- Fetched {len(response.objects)} emails via vector search ---")
        return response.objects
    except Exception as e:
        print(f"[ERROR] Native vector search failed: {e}")
        return []

def create_rag_chain_native_chat(llm):
    """Retrieves context, generates text answer, and passes context objects through."""
    
    prompt_template = """ 
    You are an assistant helping to manage emails based on provided context.
    Answer the user's question based *only* on the context below.
    Keep the answer concise and relevant to the question.

    Context:
    {context}

    Question: {question}

    Answer:
    """ 
    prompt = ChatPromptTemplate.from_template(prompt_template)

    # Step 1: Fetch and format context.
    # Output: {question, query_embedding, native_objects, context}
    fetch_and_format_context = (
        RunnablePassthrough.assign(query_embedding=RunnableLambda(lambda x: embed_query(x["question"])))
        | RunnablePassthrough.assign(native_objects=RunnableLambda(lambda x: fetch_emails_by_vector(x["query_embedding"])))
        | RunnablePassthrough.assign(context=RunnableLambda(lambda x: format_weaviate_objects_for_llm(x["native_objects"])))
    )
    
    # Step 2: Generate answer using the context dictionary from Step 1.
    # Output: string (answer_text)
    generate_answer = (
        prompt
        | llm
        | StrOutputParser()
    )

    # Combine: Run step 1, then pipe results to parallel step generating answer and passing objects
    chain = (
        fetch_and_format_context 
        | RunnableParallel(
            # Pass original native objects through
            retrieved_objects=itemgetter("native_objects"), 
            # Pass formatted context string through
            formatted_context=itemgetter("context"),
            # Generate answer using the context
            answer_text=generate_answer 
        )
    )
    # Final Output: {"retrieved_objects": [...], "formatted_context": "...", "answer_text": "..."}
    
    return chain

def create_relevance_check_chain(llm):
    """Creates a chain to check which email IDs from context are relevant to an answer."""
    parser = JsonOutputParser(pydantic_object=RelevantIDs)
    
    # Get format instructions once
    format_instructions = parser.get_format_instructions() 

    # Embed format instructions directly into the prompt string using an f-string
    # Use double curlies {{ }} for actual template variables
    prompt_template = f"""
You are an expert relevance checker. Given the Answer Text and the Formatted Context containing several emails with IDs, identify which Email IDs from the context were directly used, summarized, or quoted to generate the Answer Text.

Respond ONLY with a JSON object matching the following schema:
{format_instructions}

If no emails from the context are relevant to the Answer Text, return a JSON object with an empty list: {{"ids": []}}.

Formatted Context:
{{formatted_context}}

Answer Text:
{{answer_text}}

Relevant Email IDs (JSON object conforming to schema above):
"""
    # Create the prompt template WITHOUT partial_variables for format_instructions
    prompt = ChatPromptTemplate.from_template(
        prompt_template
        # input_variables argument removed - should be inferred from template
    )
    
    # Chain expects {"answer_text": ..., "formatted_context": ...} as input
    chain = (
        prompt
        | llm
        | parser
    )
    return chain

def fetch_emails_native(input_passthrough: dict):
    """Fetches emails using the native Weaviate client."""
    # Input is ignored, we just fetch a batch
    if not weaviate_client or not weaviate_client.is_connected():
        print("[ERROR] Native fetch failed: Weaviate client not connected.")
        return []
    try:
        print(f"--- Fetching {HOMESCREEN_EMAIL_LIMIT} emails natively for homescreen ---")
        email_collection = weaviate_client.collections.get(WEAVIATE_CLASS_NAME)
        response = email_collection.query.fetch_objects(
            limit=HOMESCREEN_EMAIL_LIMIT,
            return_properties=["sender", "subject", "received_date", "body"],
            # UUID is included by default on the object
        )
        print(f"--- Fetched {len(response.objects)} emails natively ---")
        return response.objects
    except Exception as e:
        print(f"[ERROR] Native email fetch failed: {e}")
        return []

def create_homescreen_chain_native(llm):
    """Creates a chain using native Weaviate fetch for homescreen categorization,
       incorporating user settings dynamically on each run.
    """
    parser = JsonOutputParser(pydantic_object=HomescreenData)

    # Settings are now loaded dynamically within the chain
    # try:
    #     current_settings = load_settings()
    #     ...
    # except Exception as e:
    #     ...
    #     current_settings = UserSettings()

    # Prompt now expects settings as input variables
    prompt_template = f""" 
    You are an AI assistant helping prioritize and categorize emails for a user based on the provided context and their preferences.
    Analyze the emails below (identified by ID, sender, subject, body). 
    Categorize them into 'urgent' (needs user response), 'delegate' (can be delegated), and 'waiting_on' (user is waiting for info).

    User Preferences:
    - Defines URGENT emails as: {{urgent_context}}
    - Defines DELEGATABLE emails/tasks as: {{delegate_context}}
    
    Provide your output *only* as a JSON object conforming to the schema below. For each email, include its exact 'id' (UUID).
    Schema:
    {{format_instructions}}

    Email Context:
    {{context}}

    Based *only* on the Email Context and User Preferences, identify emails for each category.
    If no emails fit a category, return an empty list for that category.
    Output *only* the JSON object.
    """ 
    
    prompt = ChatPromptTemplate.from_template(
        prompt_template,
        # Corrected AGAIN: Use single braces for the dictionary
        partial_variables={"format_instructions": parser.get_format_instructions()} 
    )

    def load_and_prepare_prompt_input(inputs: dict) -> dict:
        """Loads settings and combines with formatted context for the prompt."""
        formatted_context = inputs.get("formatted_context", "")
        try:
            settings = load_settings()
            print("--- Dynamically loaded settings for homescreen request ---")
        except Exception as e:
            print(f"[WARN] Failed to load settings dynamically: {e}. Using defaults.")
            settings = UserSettings()
            
        # Provide defaults if settings text is empty
        urgent_ctx = settings.urgent_context if settings.urgent_context else 'Not specified - use general urgency cues.'
        delegate_ctx = settings.delegate_context if settings.delegate_context else 'Not specified - use general delegation cues.'
        
        return {
            "context": formatted_context,
            "urgent_context": urgent_ctx,
            "delegate_context": delegate_ctx
        }

    # Chain: Fetch -> Format Emails -> Load Settings & Prepare Prompt Input -> Prompt -> LLM -> Parse JSON
    homescreen_chain = (
        RunnableLambda(lambda _: fetch_emails_native({})) # Fetch emails
        | RunnableLambda(format_weaviate_objects_for_llm).with_config(run_name="FormatEmailContext")  # Format them, assign name
        | RunnableLambda(lambda formatted_context: {"formatted_context": formatted_context}).with_config(run_name="PrepareContextDict") # Structure for next step
        | RunnableLambda(load_and_prepare_prompt_input).with_config(run_name="LoadSettingsAndPrepareInput") # Load settings and create prompt input dict
        | prompt
        | llm
        | parser
    )
    return homescreen_chain

# --- Global Chain Initialization --- #
# ... (moved initialization logic here) ...
rag_chain_global: RunnableParallel | None = None
relevance_check_chain_global: RunnableLambda | None = None # Keep type hint flexible
homescreen_chain_global: RunnableLambda | None = None 

# Initialization block
try:
    print(f"(Import) Connecting to Weaviate at {WEAVIATE_URL}...")
    # Choose connection method based on WEAVIATE_URL
    if WEAVIATE_URL.startswith("https://") and ".weaviate.network" in WEAVIATE_URL:
        if not os.getenv("WEAVIATE_API_KEY"):
             raise ValueError("WEAVIATE_API_KEY required for WCS connection")
        weaviate_client = weaviate.connect_to_wcs(
            cluster_url=WEAVIATE_URL,
            auth_credentials=weaviate.auth.AuthApiKey(os.getenv("WEAVIATE_API_KEY")),
             headers={"X-OpenAI-Api-Key": OPENAI_API_KEY} if OPENAI_API_KEY else {}
        )
    else: # Assume local or custom that connect_to_local handles
        weaviate_client = weaviate.connect_to_local(
             headers={"X-OpenAI-Api-Key": OPENAI_API_KEY} if OPENAI_API_KEY else {}
        )
        
    weaviate_client.is_ready() # Check connection
    print("(Import) Connected to Weaviate.")

    # Initialize LLM and Embeddings
    llm = ChatOpenAI(model=OPENAI_CHAT_MODEL, api_key=OPENAI_API_KEY, temperature=0.1) # Lower temperature for more deterministic categorization
    embeddings = OpenAIEmbeddings(model=OPENAI_EMBEDDING_MODEL, api_key=OPENAI_API_KEY)
    print("(Import) LLM and Embeddings initialized.")
    
    # Create and assign global chains
    rag_chain_global = create_rag_chain_native_chat(llm)
    relevance_check_chain_global = create_relevance_check_chain(llm)
    homescreen_chain_global = create_homescreen_chain_native(llm)
    print("(Import) RAG chains created and assigned globally.")

except Exception as e:
    # Ensure globals are None if init fails
    rag_chain_global = None
    relevance_check_chain_global = None 
    homescreen_chain_global = None
    if 'weaviate_client' in locals() and weaviate_client and weaviate_client.is_connected():
        weaviate_client.close() # Close connection if open
    weaviate_client = None
    print(f"[CRITICAL ERROR] Failed to initialize RAG components during import: {e}")
    traceback.print_exc() 
    # Optionally re-raise or exit if initialization is critical for the app to start
    # raise e 

# --- Standalone Test Block --- # 
if __name__ == "__main__":
    if not rag_chain_global or not homescreen_chain_global:
        print("Chains failed to initialize during import. Exiting test.")
    else:
        print("\n--- Testing Homescreen Chain ---")
        try:
            homescreen_result = homescreen_chain_global.invoke({})
            print("Homescreen Result:")
            import json
            print(json.dumps(homescreen_result, indent=2))
        except Exception as e:
             print(f"Homescreen test failed: {e}")
             traceback.print_exc()
        
        print("\n--- Testing Chat Chain ---")
        test_query = "What is the status of the LexAnalytica diligence?"
        print(f"Query: {test_query}")
        try:
             # Test just the RAG chain part first
             chat_result = rag_chain_global.invoke({"question": test_query})
             print("Chat RAG Result:")
             print(f"  Answer: {chat_result.get('answer_text')}")
             print(f"  Retrieved Objects: {len(chat_result.get('retrieved_objects', []))}")
             print(f"  Formatted Context Snippet: {chat_result.get('formatted_context', '')[:200]}...")
        except Exception as e:
             print(f"Chat test failed: {e}")
             traceback.print_exc()

    # Clean up client if testing standalone
    if weaviate_client and weaviate_client.is_connected():
        weaviate_client.close()
        print("\nStandalone test finished. Weaviate connection closed.") 