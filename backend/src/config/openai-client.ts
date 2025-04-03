import OpenAI from 'openai';
import dotenv from 'dotenv';

dotenv.config();

const apiKey = process.env.OPENAI_API_KEY;

if (!apiKey) {
    console.warn("Warning: OPENAI_API_KEY environment variable not set. AI Service will not function.");
}

// Initialize OpenAI client
// It will automatically use the OPENAI_API_KEY environment variable if available
const openai = new OpenAI({
    apiKey: apiKey, // Pass the key explicitly, or rely on environment variable detection
});

export default openai; 