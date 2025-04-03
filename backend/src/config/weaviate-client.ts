import weaviate, { WeaviateClient } from 'weaviate-ts-client';
import dotenv from 'dotenv';

dotenv.config();

const weaviateHost = process.env.WEAVIATE_HOST;

if (!weaviateHost) {
    console.error("Error: Missing WEAVIATE_HOST environment variable. Please check your .env file.");
    process.exit(1);
}

// Basic configuration, can be expanded later (e.g., with API keys if needed)
const client: WeaviateClient = weaviate.client({
    scheme: weaviateHost.startsWith('https') ? 'https' : 'http',
    host: weaviateHost.replace(/^https?:\/\//, ''), // Remove scheme for the client config
});

export default client; 