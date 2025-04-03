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
from langchain_core.runnables import RunnablePassthrough, RunnableParallel, RunnableLambda
from langchain_core.documents import Document # For type hinting
from pydantic import BaseModel, Field # For structured output

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
    """Creates a chain using native Weaviate fetch for homescreen categorization."""
    parser = JsonOutputParser(pydantic_object=HomescreenData)

    prompt_template = """ 
    You are an AI assistant...
    Analyze the following emails, identified by their ID, sender, subject, and body.
    Categorize them according to...
    Provide your output *only* as a JSON object...
    **IT IS ABSOLUTELY CRITICAL that for each email... include its correct 'id' (UUID). Copy the ID exactly...**
    Schema:
    {format_instructions}

    Context:
    {context}

    Based *only* on the context provided, identify...
    If no emails fit a category... return an empty list...
    Output *only* the JSON object.
    """ # (Truncated prompt from previous step for brevity)

    prompt = ChatPromptTemplate.from_template(
        prompt_template,
        partial_variables={"format_instructions": parser.get_format_instructions()})

    # Chain: Fetch Native (limit 20) -> Format Native -> Structure for Prompt -> Prompt -> LLM -> Parse JSON
    homescreen_chain = (
        # This RunnableLambda ignores input and calls fetch_emails_native directly
        RunnableLambda(lambda _: fetch_emails_native({"limit": HOMESCREEN_EMAIL_LIMIT})) # Pass limit via ignored input dict if needed, or adjust fetch_emails_native
        | RunnableLambda(format_weaviate_objects_for_llm) 
        | RunnableLambda(lambda formatted_string: {"context": formatted_string})
        | prompt
        | llm
        | parser
    )
    return homescreen_chain

# --- Main Execution Block (Adjust test for new chat chain output) ---
if __name__ == "__main__":
    # ... (Initialize client, llm, embeddings as before) ...
    try:
        print(f"Connecting to Weaviate at {WEAVIATE_URL}...")
        weaviate_client = weaviate.connect_to_local()
        weaviate_client.is_ready()
        print("Connected to Weaviate.")
    except Exception as e:
        print(f"ERROR: Could not connect to Weaviate. {e}")
        exit(1)
    
    llm = ChatOpenAI(model=OPENAI_CHAT_MODEL, api_key=OPENAI_API_KEY)
    embeddings = OpenAIEmbeddings(model=OPENAI_EMBEDDING_MODEL, api_key=OPENAI_API_KEY)
    
    # Create chains for testing
    rag_chain_native = create_rag_chain_native_chat(llm)
    relevance_chain = create_relevance_check_chain(llm)
    homescreen_chain_native = create_homescreen_chain_native(llm)
    print("\nRAG Email Assistant Initialized for standalone execution.")

    # --- Test Native Chat Chain + Relevance Check ---
    print("Example Queries (Chat + Relevance Check):")
    queries = [
        "Any urgent items?",
    ]
    for query in queries:
        print(f"\n--- Query: {query} ---")
        try:
            # Step 1: Get answer and context objects
            rag_result = rag_chain_native.invoke({"question": query})
            answer = rag_result.get('answer_text')
            objects = rag_result.get('retrieved_objects', [])
            context_str = rag_result.get('formatted_context', '') # Get formatted context too
            print(f"\nAssistant Answer Text: {answer}")
            print(f"Retrieved Objects Count: {len(objects)}")

            # Step 2: Run relevance check
            if answer and context_str:
                print("\n--- Running Relevance Check --- ")
                relevance_input = {"answer_text": answer, "formatted_context": context_str}
                relevance_result = relevance_chain.invoke(relevance_input)
                relevant_ids = relevance_result.get('ids', [])
                print(f"Relevance Check Result (IDs): {relevant_ids}")
                
                # Step 3: (Simulate main.py) Build final references
                final_refs = []
                for obj in objects:
                    if str(obj.uuid) in relevant_ids:
                        final_refs.append({"id": str(obj.uuid), "subject": obj.properties.get("subject", "N/A")})
                print(f"Final References based on Relevance Check: {final_refs}")
            else:
                 print("Skipping relevance check (no answer or context).")

        except Exception as e:
            print(f"An error occurred processing the query: {e}")

    # --- Test Homescreen Chain --- 
    print("\n--- Testing Homescreen Categorization (Native Fetch) --- ")
    try:
        homescreen_result = homescreen_chain_native.invoke({})
        print("\nCategorized Data (Native):")
        import json
        print(json.dumps(homescreen_result, indent=2))
    except Exception as e:
         print(f"An error occurred processing homescreen chain: {e}")

    # Close Weaviate client connection
    if weaviate_client and weaviate_client.is_connected():
        weaviate_client.close()
        print("\nWeaviate connection closed.")
else:
    # --- Initialization for Import ---
    try:
        print("(Import) Connecting to Weaviate...")
        weaviate_client = weaviate.connect_to_local()
        weaviate_client.is_ready()
        print("(Import) Connected to Weaviate.")
        llm = ChatOpenAI(model=OPENAI_CHAT_MODEL, api_key=OPENAI_API_KEY)
        embeddings = OpenAIEmbeddings(model=OPENAI_EMBEDDING_MODEL, api_key=OPENAI_API_KEY)
        
        # Create the chain instances for export
        rag_chain_global = create_rag_chain_native_chat(llm) 
        # Add the relevance check chain
        relevance_check_chain_global = create_relevance_check_chain(llm)
        homescreen_chain_global = create_homescreen_chain_native(llm)
        print("(Import) RAG chains created (including relevance check chain).")

    except Exception as e:
        print(f"ERROR during import initialization: {e}")
        traceback.print_exc() # Print the full traceback
        rag_chain_global = None
        relevance_check_chain_global = None # Ensure this is None on error
        homescreen_chain_global = None
        weaviate_client = None
        embeddings = None

# --- Main Execution Block (Adjust tests if needed) ---
if __name__ == "__main__":
    # ... (Initialize client, llm, embeddings) ...
    try:
        print(f"Connecting to Weaviate at {WEAVIATE_URL}...")
        weaviate_client = weaviate.connect_to_local()
        weaviate_client.is_ready()
        print("Connected to Weaviate.")
    except Exception as e:
        print(f"ERROR: Could not connect to Weaviate. {e}")
        exit(1)
    
    llm = ChatOpenAI(model=OPENAI_CHAT_MODEL, api_key=OPENAI_API_KEY)
    embeddings = OpenAIEmbeddings(model=OPENAI_EMBEDDING_MODEL, api_key=OPENAI_API_KEY)
    
    # Create chains for testing
    rag_chain_native = create_rag_chain_native_chat(llm)
    relevance_chain = create_relevance_check_chain(llm)
    homescreen_chain_native = create_homescreen_chain_native(llm)
    print("\nRAG Email Assistant Initialized for standalone execution.")

    # --- Test Native Chat Chain + Relevance Check ---
    print("Example Queries (Chat + Relevance Check):")
    queries = [
        "Any urgent items?",
    ]
    for query in queries:
        print(f"\n--- Query: {query} ---")
        try:
            # Step 1: Get answer and context objects
            rag_result = rag_chain_native.invoke({"question": query})
            answer = rag_result.get('answer_text')
            objects = rag_result.get('retrieved_objects', [])
            context_str = rag_result.get('formatted_context', '') # Get formatted context too
            print(f"\nAssistant Answer Text: {answer}")
            print(f"Retrieved Objects Count: {len(objects)}")

            # Step 2: Run relevance check
            if answer and context_str:
                print("\n--- Running Relevance Check --- ")
                relevance_input = {"answer_text": answer, "formatted_context": context_str}
                relevance_result = relevance_chain.invoke(relevance_input)
                relevant_ids = relevance_result.get('ids', [])
                print(f"Relevance Check Result (IDs): {relevant_ids}")
                
                # Step 3: (Simulate main.py) Build final references
                final_refs = []
                for obj in objects:
                    if str(obj.uuid) in relevant_ids:
                        final_refs.append({"id": str(obj.uuid), "subject": obj.properties.get("subject", "N/A")})
                print(f"Final References based on Relevance Check: {final_refs}")
            else:
                 print("Skipping relevance check (no answer or context).")

        except Exception as e:
            print(f"An error occurred processing the query: {e}")

    # --- Test Homescreen Chain --- 
    # ... (Homescreen test remains the same) ...

    # Close Weaviate client connection
    # ... (Cleanup remains the same) ... 