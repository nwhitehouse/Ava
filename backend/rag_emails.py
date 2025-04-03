import os
import weaviate
from dotenv import load_dotenv
from operator import itemgetter

# LangChain imports
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_weaviate.vectorstores import WeaviateVectorStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
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

# Check for API Key
if not OPENAI_API_KEY:
    print("ERROR: OPENAI_API_KEY environment variable not set.")
    exit(1)

# --- Pydantic Models for Structured Output ---
class EmailInfo(BaseModel):
    subject: str = Field(description="The subject line of the email")
    sender: str = Field(description="The sender of the email")
    reasoning: str = Field(description="Brief reason why this email fits the category")

class HomescreenData(BaseModel):
    urgent: list[EmailInfo] = Field(description="List of emails needing urgent response from me", default=[])
    delegate: list[EmailInfo] = Field(description="List of emails that can potentially be delegated", default=[])
    waiting_on: list[EmailInfo] = Field(description="List of emails where I am waiting for information from someone else", default=[])

# --- Initialize LangChain Components ---

# Weaviate Client (ensure your Weaviate instance is running)
try:
    print(f"Connecting to Weaviate at {WEAVIATE_URL}...")
    client = weaviate.connect_to_local()
    # Optional: Check connection
    client.is_ready()
    print("Connected to Weaviate.")
except Exception as e:
    print(f"ERROR: Could not connect to Weaviate. Please ensure it's running. {e}")
    exit(1)

# OpenAI Models
llm = ChatOpenAI(model=OPENAI_CHAT_MODEL, api_key=OPENAI_API_KEY)
embeddings = OpenAIEmbeddings(model=OPENAI_EMBEDDING_MODEL, api_key=OPENAI_API_KEY)

# Weaviate Vector Store connected to LangChain
# We specify the text property to use for search/retrieval
vectorstore = WeaviateVectorStore(
    client=client,
    index_name=WEAVIATE_CLASS_NAME, # The Weaviate class name
    text_key="body", # Use the 'body' property for similarity search
    embedding=embeddings, # Use OpenAI embeddings for queries
    # Specify attributes to retrieve along with the vector search results
    attributes=["sender", "subject", "received_date"]
)

# Retriever (gets relevant documents)
# search_kwargs='k': 5 retrieves top 5 most similar emails
retriever = vectorstore.as_retriever(search_kwargs={'k': 5})

# --- RAG Chain Definition ---

def format_docs(docs: list[Document]) -> str:
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

def create_rag_chain(retriever, llm):
    """Creates the main RAG chain for answering questions based on retrieved emails."""
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
        RunnablePassthrough.assign(context=(lambda x: format_docs(x["context"])))
        | prompt
        | llm
        | StrOutputParser()
    )

    rag_chain_with_source = RunnableParallel(
        {"context": retriever, "question": RunnablePassthrough()}
    ).assign(answer=rag_chain_from_docs)

    return rag_chain_with_source

def create_homescreen_chain(retriever, llm):
    """Creates a RAG chain that categorizes emails and returns structured JSON output."""

    # Increase retrieved docs for better categorization context
    categorization_retriever = retriever.with_config(search_kwargs={'k': 15})

    parser = JsonOutputParser(pydantic_object=HomescreenData)

    prompt_template = """
You are an AI assistant tasked with categorizing emails based on provided context.
Analyze the following emails and categorize them according to these definitions:
- urgent: Emails that require *my* immediate attention or response soon.
- delegate: Emails tasks or information requests that someone else could potentially handle.
- waiting_on: Emails where I am waiting for a response or information from the sender or others mentioned.

Provide your output *only* as a JSON object matching the following schema:
{format_instructions}

Context:
{context}

Based *only* on the context provided, identify:
- Up to 5 urgent emails.
- Up to 3 delegate emails.
- Up to 3 waiting_on emails.

If no emails fit a category based on the context, return an empty list for that category.
Do not make assumptions beyond the email text. For example, don't assume a project update requires urgent action unless the text implies it.
"""

    prompt = ChatPromptTemplate.from_template(
        prompt_template,
        partial_variables={"format_instructions": parser.get_format_instructions()})

    # Chain: Retrieve -> Format Context -> Fill Prompt -> Call LLM -> Parse JSON
    homescreen_chain = (
        {"context": categorization_retriever | format_docs} # Retrieve and format
        | prompt
        | llm
        | parser
    )
    return homescreen_chain

# --- Main Execution / Example Usage (Adjusted) ---
if __name__ == "__main__":
    # --- Initialization (as before) ---
    # Weaviate Client
    try:
        print(f"Connecting to Weaviate at {WEAVIATE_URL}...")
        client = weaviate.connect_to_local()
        client.is_ready()
        print("Connected to Weaviate.")
    except Exception as e:
        print(f"ERROR: Could not connect to Weaviate. {e}")
        exit(1)
    # OpenAI Models
    llm = ChatOpenAI(model=OPENAI_CHAT_MODEL, api_key=OPENAI_API_KEY)
    embeddings = OpenAIEmbeddings(model=OPENAI_EMBEDDING_MODEL, api_key=OPENAI_API_KEY)
    # Vector Store & Retriever
    vectorstore = WeaviateVectorStore(
        client=client,
        index_name=WEAVIATE_CLASS_NAME,
        text_key="body",
        embedding=embeddings,
        attributes=["sender", "subject", "received_date"]
    )
    retriever = vectorstore.as_retriever(search_kwargs={'k': 5})
    # --- Create the chains ---
    rag_chain = create_rag_chain(retriever, llm)
    homescreen_chain = create_homescreen_chain(retriever, llm)
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
    # --- Test Homescreen Chain ---
    print("\n--- Testing Homescreen Categorization --- ")
    try:
        # Note: Input for this chain is ignored as the prompt is fixed for categorization
        homescreen_result = homescreen_chain.invoke("Categorize emails for homescreen")
        print("\nCategorized Data:")
        import json
        print(json.dumps(homescreen_result, indent=2))
    except Exception as e:
         print(f"An error occurred processing homescreen chain: {e}")
    # Close Weaviate client connection
    if client.is_connected():
        client.close()
        print("\nWeaviate connection closed.")
else:
    # --- Initialization for Import ---
    # Ensure components are initialized when imported by FastAPI
    try:
        print("(Import) Connecting to Weaviate...")
        client = weaviate.connect_to_local()
        client.is_ready()
        print("(Import) Connected to Weaviate.")
        llm = ChatOpenAI(model=OPENAI_CHAT_MODEL, api_key=OPENAI_API_KEY)
        embeddings = OpenAIEmbeddings(model=OPENAI_EMBEDDING_MODEL, api_key=OPENAI_API_KEY)
        vectorstore = WeaviateVectorStore(
            client=client,
            index_name=WEAVIATE_CLASS_NAME,
            text_key="body",
            embedding=embeddings,
            attributes=["sender", "subject", "received_date"]
        )
        # Use standard retriever setting for general chain
        retriever_k5 = vectorstore.as_retriever(search_kwargs={'k': 5})
        # Use potentially different retriever settings for categorization
        retriever_k15 = vectorstore.as_retriever(search_kwargs={'k': 15}) # More context

        # Create the chain instances for export
        rag_chain_global = create_rag_chain(retriever_k5, llm)
        homescreen_chain_global = create_homescreen_chain(retriever_k15, llm) # Pass appropriate retriever
        print("(Import) RAG chains created.")

    except Exception as e:
        print(f"ERROR during import initialization: {e}")
        # Handle error appropriately, maybe raise it or set a flag
        rag_chain_global = None
        homescreen_chain_global = None
        client = None # Ensure client is None if connection failed 