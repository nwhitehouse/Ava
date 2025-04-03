import openai from '../config/openai-client';
// Import specific types from the openai package
import {
    ChatCompletionMessageParam,
    ChatCompletionChunk // Import ChatCompletionChunk
} from 'openai/resources/chat/completions';
import { APIError } from 'openai';
import { Stream } from 'openai/streaming'; // Import Stream type

class AIService {

    /**
     * Gets a stream of chat completion responses from OpenAI.
     * @param userMessage The message from the user.
     * @param systemPrompt Optional system prompt to guide the AI.
     * @returns A stream object or null if an error occurs.
     */
    async getChatCompletionStream(
        userMessage: string,
        systemPrompt?: string
    ): Promise<Stream<ChatCompletionChunk> | null> {
        const apiKey = process.env.OPENAI_API_KEY;
        if (!apiKey) {
            console.error("OpenAI API key not configured. Cannot get chat completion stream.");
            // In a real app, might throw an error instead of returning null
            return null;
        }

        const messages: ChatCompletionMessageParam[] = [];
        if (systemPrompt) {
            messages.push({ role: 'system', content: systemPrompt });
        }
        messages.push({ role: 'user', content: userMessage });

        try {
            console.log("[AI Service] Requesting stream from OpenAI...");
            const stream = await openai.chat.completions.create({
                model: "gpt-3.5-turbo", // Or gpt-4o-mini
                messages: messages,
                temperature: 0.7,
                max_tokens: 300, // Can increase max_tokens for streams
                stream: true, // Enable streaming
            });
            console.log("[AI Service] Stream connection established.");
            return stream;
        } catch (error: any) {
            console.error("[AI Service] Error getting chat completion stream:", error);
            // Propagate the error or handle it
            // Returning null for now, route handler needs to check this
            return null;
        }
    }

    /**
     * Gets a chat completion response from OpenAI.
     * @param userMessage The message from the user.
     * @param systemPrompt Optional system prompt to guide the AI.
     * @returns The AI's response content or a user-friendly error message.
     */
    async getChatCompletion(userMessage: string, systemPrompt?: string): Promise<string> {
        const apiKey = process.env.OPENAI_API_KEY;
        if (!apiKey) {
            console.error("OpenAI API key not configured. Cannot get chat completion.");
            return "AI Service is not configured. Please set the OPENAI_API_KEY.";
        }

        // Use the imported type directly
        const messages: ChatCompletionMessageParam[] = [];

        if (systemPrompt) {
            messages.push({ role: 'system', content: systemPrompt });
        }
        messages.push({ role: 'user', content: userMessage });

        try {
            console.log("[AI Service] Sending request to OpenAI...");
            const completion = await openai.chat.completions.create({
                // Consider using gpt-4o-mini for faster/cheaper responses initially
                model: "gpt-3.5-turbo",
                messages: messages,
                temperature: 0.7, // Adjust creativity vs. determinism
                max_tokens: 150, // Limit response length
            });

            const responseContent = completion.choices[0]?.message?.content;
            console.log("[AI Service] Received response from OpenAI.");
            // Ensure a string is always returned
            return responseContent ?? "AI did not return a valid response.";

        } catch (error: any) {
            console.error("[AI Service] Error fetching chat completion:", error);
            // Use the imported APIError type for checking
            if (error instanceof APIError) {
                return `AI API Error: ${error.status} - ${error.message}`;
            }
            return "An error occurred while communicating with the AI.";
        }
    }

    // Future methods for summarization, task extraction, etc. can go here
    // async summarizeEmail(emailContent: string): Promise<string | null> { ... }
    // async extractTasks(emailContent: string): Promise<string[] | null> { ... }
}

// Export a singleton instance of the service
export const aiService = new AIService(); 