import random
from datetime import datetime, timedelta
import weaviate
import weaviate.classes as wvc
from weaviate.exceptions import UnexpectedStatusCodeError
import os
from dotenv import load_dotenv
from openai import OpenAI
import json
import time

# Load environment variables (from backend/.env or .env)
load_dotenv()

# --- Configuration ---
WEAVIATE_URL = "http://localhost:8080"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
WEAVIATE_CLASS_NAME = "Email"
BATCH_SIZE = 10 # Process emails in batches for Weaviate

# --- Email Generation (Keep the existing function) ---
def generate_sample_emails(num_emails=50):
    """Generates a list of diverse sample email dictionaries."""

    senders = [
        "no-reply@important-updates.com", "newsletter@techcrunch.io", "support@your-bank.com",
        "hr@companya.com", "john.doe@clientcorp.com", "jane.smith@partnerfirm.com",
        "marketing@cool-tool.io", "alert@monitoring-system.cloud", "boss@companya.com",
        "colleague1@companya.com", "colleague2@companya.com", "recruiter@jobsearch.com",
        "conference-updates@eventbrite-reg.com", "billing@utility-provider.net", "friend@personal-mail.com",
        "family@family-domain.org", "travel-agent@bookings.com", "project-manager@companya.com",
        "it-support@companya.com", "random-promo@retailer-xyz.biz"
    ]

    subjects = [
        "Action Required: Update Your Account Details", "Weekly Tech Digest", "Security Alert: Unusual Login Detected",
        "Company Town Hall Reminder", "Re: Project Phoenix Proposal", "Follow Up: Partnership Discussion",
        "New Feature Launch: Try Our AI Assistant!", "CRITICAL: Server CPU Usage High", "Urgent: Need Your Approval ASAP",
        "Quick Question about the Report", "Team Lunch next Friday?", "Job Opportunity: Senior Engineer",
        "Your Conference Ticket Confirmation", "Your Monthly Bill is Ready", "Catch up soon?",
        "Vacation Photos!", "Your Flight Itinerary", "Project Redwood - Status Update",
        "Password Reset Request", "FLASH SALE: 50% Off Everything!"
    ]

    body_templates = [
        # Formal/Action Required
        "Dear User,\nPlease take a moment to review and update your account information [link]. This is required for security purposes. Failure to update by [date] may result in account suspension.\nSincerely,\nThe Team",
        "A login attempt from an unrecognized device occurred at [time] on [date]. If this wasn't you, please secure your account immediately [link].\nRegards,\nSecurity Team",
        "Hello Team,\nThis is a reminder about the mandatory company town hall scheduled for [date] at [time]. Please ensure you attend.\nBest,\nHR Department",
        "Hi [Name],\nCould you please review and approve the attached budget proposal by end of day today? It's critical for the project timeline.\nThanks,\n[Boss Name]",
        "To maintain service quality, we require you to update your payment information [link]. Please do so within 48 hours.\nThank you,\nBilling Department",

        # Project/Work Related
        "Hi [Name],\nThanks for sending over the proposal. I've reviewed it and have a few comments (see attached). Can we sync briefly tomorrow morning?\nBest,\nJohn Doe",
        "Hi Jane,\nFollowing up on our discussion last week regarding the potential partnership. Are you available for a quick call next Tuesday to finalize details?\nRegards,\n[My Name]",
        "Hi Team,\nHere's the latest status update for Project Redwood:\n- Milestone 1: Completed\n- Milestone 2: On track, 75% done\n- Blocker: Waiting for feedback from ClientCorp\nPlease let me know if you have any questions.\nThanks,\nProject Manager",
        "Hey,\nJust wondering if you had a chance to look at the Q3 report draft I sent yesterday? Need your feedback before the meeting.\nCheers,\nColleague",
        "Folks,\nLet's do a team lunch next Friday to celebrate the successful launch! How about 12:30 PM at [Restaurant]? Let me know if that works.\nBest,\nColleague",

        # Informational/Updates
        "Here's your weekly summary of the top stories in tech: [Link 1], [Link 2], [Link 3].\nEnjoy reading,\nTechCrunch Newsletter",
        "We're excited announce our new AI-powered assistant! It can help you [feature 1], [feature 2]. Try it out today! [link]\nCheers,\nCool Tool Team",
        "ALERT: CPU usage on server [Server Name] has exceeded 90% for the past 15 minutes. Please investigate immediately.\nMonitoring System",
        "Dear Attendee,\nThank you for registering for [Conference Name]! Your ticket is attached. Find more event details here: [link].\nSee you there!",
        "Your bill for the period ending [date] is now available online. Amount due: [Amount]. View details: [link]\nUtility Provider",

        # Personal/Misc
        "Hey!\nLong time no see! How have you been? We should grab coffee sometime next week if you're free.\nBest,\nFriend",
        "Hi everyone,\nJust wanted to share some photos from our recent trip! [link to album]\nHope you enjoy them!\nLove,\nFamily Member",
        "Your flight booking [Confirmation Number] is confirmed. Please review the attached itinerary.\nTravel Agent",
        "Hello [My Name],\nI came across your profile and thought your experience might be a great fit for a Senior Engineer role at [Company]. Would you be open to a brief chat? \nRegards,\nRecruiter",
        "DON'T MISS OUT! Get 50% off sitewide during our limited-time flash sale! Shop now: [link]\nRetailer XYZ"
    ]

    emails = []
    start_date = datetime.now()

    for i in range(num_emails):
        sender = random.choice(senders)
        subject = random.choice(subjects)
        body = random.choice(body_templates)
        # Basic personalization placeholders
        body = body.replace("[link]", "https://example.com")
        body = body.replace("[date]", (start_date - timedelta(days=random.randint(1, 5))).strftime('%Y-%m-%d'))
        body = body.replace("[time]", f"{random.randint(9, 17)}:{random.randint(0, 59):02d}")
        body = body.replace("[Name]", random.choice(["Alex", "Bob", "Charlie", "Team"]))
        body = body.replace("[Boss Name]", "My Boss")
        body = body.replace("[Restaurant]", "The Corner Cafe")
        body = body.replace("[Server Name]", f"webserver-{random.randint(1,3)}")
        body = body.replace("[Conference Name]", "Tech Summit 2024")
        body = body.replace("[Amount]", f"${random.uniform(20, 500):.2f}")
        body = body.replace("[Confirmation Number]", f"{random.randint(100000, 999999)}")
        body = body.replace("[Company]", "AnotherCorp")

        email_date = start_date - timedelta(days=random.randint(0, 30), hours=random.randint(0,23))

        emails.append({
            "id": f"email_{i+1:03d}", # Simple sequential ID
            "sender": sender,
            "subject": subject,
            "body": body,
            "received_date": email_date.isoformat() # Store date as ISO string
        })

    return emails

# --- Weaviate Schema Definition ---
def define_weaviate_schema(client: weaviate.WeaviateClient):
    """Defines and creates the Email schema in Weaviate if it doesn't exist."""
    try:
        client.collections.get(WEAVIATE_CLASS_NAME)
        print(f"Class '{WEAVIATE_CLASS_NAME}' already exists.")
    except UnexpectedStatusCodeError:
        print(f"Class '{WEAVIATE_CLASS_NAME}' does not exist. Creating...")
        client.collections.create(
            name=WEAVIATE_CLASS_NAME,
            properties=[
                wvc.Property(name="sender", data_type=wvc.DataType.TEXT),
                wvc.Property(name="subject", data_type=wvc.DataType.TEXT),
                wvc.Property(name="body", data_type=wvc.DataType.TEXT),
                # Use TEXT for ISO format date, Date type can be tricky
                wvc.Property(name="received_date", data_type=wvc.DataType.TEXT),
            ],
            # Specify no internal vectorizer, we provide vectors externally
            vectorizer_config=wvc.Configure.Vectorizer.none()
        )
        print(f"Class '{WEAVIATE_CLASS_NAME}' created.")

# --- OpenAI Embedding Function ---
def get_openai_embedding(text: str, client: OpenAI) -> list[float]:
    """Generates embedding for the given text using OpenAI API."""
    text = text.replace("\n", " ") # API recommendation
    try:
        response = client.embeddings.create(input=[text], model=OPENAI_EMBEDDING_MODEL)
        return response.data[0].embedding
    except Exception as e:
        print(f"Error getting embedding for text: '{text[:50]}...'")
        print(e)
        return [] # Return empty list on error

# --- Data Ingestion Logic ---
def ingest_emails(client: weaviate.WeaviateClient, openai_client: OpenAI, emails: list):
    """Ingests emails into Weaviate with externally generated embeddings."""
    define_weaviate_schema(client) # Ensure schema exists
    email_collection = client.collections.get(WEAVIATE_CLASS_NAME)

    print(f"Starting ingestion of {len(emails)} emails...")
    with email_collection.batch.dynamic() as batch:
        count = 0
        for email in emails:
            # Combine relevant fields for embedding
            text_to_embed = f"Subject: {email['subject']}\nSender: {email['sender']}\n\n{email['body']}"

            # Get embedding from OpenAI
            vector = get_openai_embedding(text_to_embed, openai_client)

            if not vector:
                print(f"Skipping email id {email['id']} due to embedding error.")
                continue # Skip if embedding failed

            # Prepare properties dictionary for Weaviate
            properties = {
                "sender": email["sender"],
                "subject": email["subject"],
                "body": email["body"],
                "received_date": email["received_date"],
            }

            # Add object to batch
            batch.add_object(
                properties=properties,
                vector=vector
                # Weaviate generates UUID if not provided
            )
            count += 1
            if count % BATCH_SIZE == 0:
                print(f"Processed {count}/{len(emails)} emails...")
                # Batch auto-executes, but a small pause can help rate limits
                time.sleep(0.5)

    print(f"\nFinished ingestion. Added {count} emails to Weaviate class '{WEAVIATE_CLASS_NAME}'.")
    # Check for batch errors (optional but recommended)
    if batch.number_errors > 0:
        print(f"WARNING: Encountered {batch.number_errors} errors during batch import.")
        # You might want to inspect batch.errors for details

# --- Main Execution ---
if __name__ == "__main__":
    if not OPENAI_API_KEY:
        print("ERROR: OPENAI_API_KEY environment variable not set.")
        exit(1)

    print("Generating sample emails...")
    sample_emails = generate_sample_emails(50)
    print(f"Generated {len(sample_emails)} emails.")

    try:
        # Initialize OpenAI client
        openai_client = OpenAI(api_key=OPENAI_API_KEY)

        # Connect to Weaviate
        print(f"Connecting to Weaviate at {WEAVIATE_URL}...")
        weaviate_client = weaviate.connect_to_local()
        # Or use: weaviate.connect_to_custom(http_host=WEAVIATE_URL.split('//')[1].split(':')[0], http_port=int(WEAVIATE_URL.split(':')[2]), grpc_port=50051) # If needed
        print("Connected to Weaviate.")

        # Ingest data
        ingest_emails(weaviate_client, openai_client, sample_emails)

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if 'weaviate_client' in locals() and weaviate_client.is_connected():
            weaviate_client.close()
            print("Weaviate connection closed.") 