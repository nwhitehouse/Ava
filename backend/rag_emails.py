import os
import weaviate
import weaviate.classes as wvc # Keep this import for fetch_objects
from dotenv import load_dotenv
from operator import itemgetter

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
    subject: str = Field(description="The subject line of the email")
    sender: str = Field(description="The sender of the email")
    reasoning: str = Field(description="Brief reason why this email fits the category")

class HomescreenData(BaseModel):
    urgent: list[EmailInfo] = Field(description="List of emails needing urgent response from me", default=[])
    delegate: list[EmailInfo] = Field(description="List of emails that can potentially be delegated", default=[])
    waiting_on: list[EmailInfo] = Field(description="List of emails where I am waiting for information from someone else", default=[])

# --- Global Weaviate Client (Initialized later if imported) --- 
weaviate_client: weaviate.WeaviateClient | None = None

# --- Helper Functions ---

def format_docs_lc(docs: list[Document]) -> str:
    """Formats LangChain Documents for context."""
    # This is used by the general RAG chain, doesn't need UUID handling here
    # Assuming general RAG doesn't need clickable IDs for now
    formatted_list = []
    for i, doc in enumerate(docs):
        metadata = doc.metadata
        entry = (
            f"Email {i+1}:\n" +
            f"  Sender: {metadata.get('sender', 'N/A')}\n" +
            f"  Subject: {metadata.get('subject', 'N/A')}\n" +
            f"  Date: {metadata.get('received_date', 'N/A')}\n" +
            f"  Body: {doc.page_content}"
        )
        formatted_list.append(entry)
    return "\n---\n".join(formatted_list)

def format_weaviate_objects_for_llm(objects) -> str:
    """Formats native Weaviate objects for LLM context, ensuring UUID is included."""
    formatted_list = []
    print("--- Formatting Weaviate Objects for Homescreen LLM Context ---") # DEBUG
    for i, obj in enumerate(objects):
        # Native client stores UUID directly on the object
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

def create_rag_chain(retriever, llm):
    """Creates the main RAG chain using LangChain retriever."""
    prompt_template = """
    You are an assistant helping to manage emails.
    Use the following retrieved email context to answer the question.
    If you don't know the answer from the context, just say that you don't know.
    Keep the answer concise and based *only* on the provided context.

    Context:
    {context}

    Question: {question}

    Answer:
    """
    prompt = ChatPromptTemplate.from_template(prompt_template)

    rag_chain_from_docs = (
        RunnablePassthrough.assign(context=(lambda x: format_docs_lc(x["context"])))
        | prompt
        | llm
        | StrOutputParser()
    )

    rag_chain_with_source = RunnableParallel(
        {"context": retriever, "question": RunnablePassthrough()}
    ).assign(answer=rag_chain_from_docs)

    return rag_chain_with_source

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
    """ # (Using truncated prompt from previous step for brevity)

    prompt = ChatPromptTemplate.from_template(
        prompt_template,
        partial_variables={"format_instructions": parser.get_format_instructions()})

    # Chain: Fetch Native -> Format Native -> Structure for Prompt -> Prompt -> LLM -> Parse JSON
    homescreen_chain = (
        RunnableLambda(fetch_emails_native)
        | RunnableLambda(format_weaviate_objects_for_llm)
        # Transform the formatted string output into a dict with the key 'context'
        | RunnableLambda(lambda formatted_string: {"context": formatted_string})
        | prompt # Prompt now correctly receives {"context": ...}
        | llm
        | parser
    )
    return homescreen_chain

# --- Main Execution Block (for standalone testing, might need adjustments) ---
if __name__ == "__main__":
    # Assign to global client for testing
    try:
        print(f"Connecting to Weaviate at {WEAVIATE_URL}...")
        weaviate_client = weaviate.connect_to_local()
        weaviate_client.is_ready()
        print("Connected to Weaviate.")
    except Exception as e:
        print(f"ERROR: Could not connect to Weaviate. {e}")
        exit(1)
    
    llm = ChatOpenAI(model=OPENAI_CHAT_MODEL, api_key=OPENAI_API_KEY)
    # Initialize retriever for standard RAG test
    embeddings = OpenAIEmbeddings(model=OPENAI_EMBEDDING_MODEL, api_key=OPENAI_API_KEY)
    vectorstore = WeaviateVectorStore(
        client=weaviate_client,
        index_name=WEAVIATE_CLASS_NAME,
        text_key="body",
        embedding=embeddings,
        attributes=["sender", "subject", "received_date"] # Keep simple for general chat
    )
    retriever = vectorstore.as_retriever(search_kwargs={'k': 5})
    
    # Create chains for testing
    rag_chain = create_rag_chain(retriever, llm)
    homescreen_chain_native = create_homescreen_chain_native(llm)
    print("\nRAG Email Assistant Initialized for standalone execution.")

    # --- Test Standard Chain ---
    print("Example Queries (Standard RAG):")
    queries = [
        "Summarize the main topics in my recent emails.",
        "Which emails seem urgent or require immediate action?",
    ]
    for query in queries:
        print(f"\n--- Query: {query} ---")
        try:
            result = rag_chain.invoke(query)
            print("\nAssistant Answer:")
            print(result['answer'])
        except Exception as e:
            print(f"An error occurred processing the query: {e}")

    # --- Test Homescreen Chain (Native) ---
    print("\n--- Testing Homescreen Categorization (Native Fetch) --- ")
    try:
        # Input is ignored by fetch_emails_native
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
    # Ensure components are initialized when imported by FastAPI
    try:
        print("(Import) Connecting to Weaviate...")
        # Assign to the global client variable
        weaviate_client = weaviate.connect_to_local()
        weaviate_client.is_ready()
        print("(Import) Connected to Weaviate.")
        llm = ChatOpenAI(model=OPENAI_CHAT_MODEL, api_key=OPENAI_API_KEY)
        embeddings = OpenAIEmbeddings(model=OPENAI_EMBEDDING_MODEL, api_key=OPENAI_API_KEY)
        
        # Initialize LangChain VectorStore and Retriever for general chat RAG
        vectorstore = WeaviateVectorStore(
            client=weaviate_client,
            index_name=WEAVIATE_CLASS_NAME,
            text_key="body",
            embedding=embeddings,
            attributes=["sender", "subject", "received_date"] # Keep simple for general chat
        )
        retriever_k5 = vectorstore.as_retriever(search_kwargs={'k': 5})

        # Create the chain instances for export
        rag_chain_global = create_rag_chain(retriever_k5, llm)
        # Use the NATIVE fetch chain for homescreen
        homescreen_chain_global = create_homescreen_chain_native(llm)
        print("(Import) RAG chains created (using native fetch for homescreen).")

    except Exception as e:
        print(f"ERROR during import initialization: {e}")
        rag_chain_global = None
        homescreen_chain_global = None
        weaviate_client = None 