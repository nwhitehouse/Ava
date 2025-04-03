import os
import weaviate
from dotenv import load_dotenv
from operator import itemgetter

# LangChain imports
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_weaviate.vectorstores import WeaviateVectorStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.documents import Document # For type hinting

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

# --- Define RAG Chain ---

# Prompt Template
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

# Helper function to format retrieved documents
def format_docs(docs: list[Document]) -> str:
    formatted_list = []
    for i, doc in enumerate(docs):
        # Access metadata stored during ingestion
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

# RAG Chain using LangChain Expression Language (LCEL)
rag_chain_from_docs = (
    RunnablePassthrough.assign(context=(lambda x: format_docs(x["context"])))
    | prompt
    | llm
    | StrOutputParser()
)

# Complete RAG chain that includes retrieval
# Takes a question -> Retrieves docs -> Formats docs -> Fills prompt -> Calls LLM -> Parses output
rag_chain_with_source = RunnableParallel(
    {"context": retriever, "question": RunnablePassthrough()}
).assign(answer=rag_chain_from_docs)

# --- Example Usage ---
if __name__ == "__main__":
    print("\nRAG Email Assistant Initialized.")
    print("Example Queries:")

    queries = [
        "Summarize the main topics in my recent emails.",
        "Which emails seem urgent or require immediate action?",
        "Are there any emails about project updates or reports?",
        "Identify emails that I could potentially delegate to someone else.",
        "Which emails are reminders or notifications (like bills or events)?",
        "What are the emails about project phoenix?", # Specific query
        "Find emails regarding billing or payments."
    ]

    for query in queries:
        print(f"\n--- Query: {query} ---")
        try:
            # Invoke the chain. It handles retrieval and generation.
            # We ask for the 'answer' part of the parallel chain's output.
            result = rag_chain_with_source.invoke(query)
            print("\nAssistant Answer:")
            print(result['answer'])

            # Optionally print retrieved source documents for verification
            # print("\nRetrieved Context:")
            # print(format_docs(result['context']))

        except Exception as e:
            print(f"An error occurred processing the query: {e}")

    # Close Weaviate client connection
    if client.is_connected():
        client.close()
        print("\nWeaviate connection closed.") 