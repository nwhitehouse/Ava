import { Router, Request, Response, RequestHandler, NextFunction } from 'express';
import { aiService } from '../services/ai.service'; // Import AI service

const router = Router();

// GET /api/chat - Changed to GET for EventSource, message via query param
const handleChatMessageStream: RequestHandler = async (req, res, next: NextFunction): Promise<void> => {
    // Get message from query parameter
    const message = req.query.message as string;

    if (!message || typeof message !== 'string') {
        res.status(400).json({ error: 'Invalid or missing message query parameter' });
        return;
    }

    console.log(`[Chat API Stream] Received: "${message}"`);

    try {
        const systemPrompt = "You are a helpful email assistant.";
        const stream = await aiService.getChatCompletionStream(message, systemPrompt);

        if (!stream) {
            // Write an SSE error event before closing
            res.writeHead(500, { 'Content-Type': 'text/event-stream' });
            res.write(`data: ${JSON.stringify({ error: 'Failed to establish connection with AI service.' })}\n\n`);
            res.end();
            return;
        }

        // Set headers for SSE
        res.setHeader('Content-Type', 'text/event-stream');
        res.setHeader('Cache-Control', 'no-cache');
        res.setHeader('Connection', 'keep-alive');
        res.flushHeaders();

        // Handle client disconnect
        req.on('close', () => {
            console.log("[Chat API Stream] Client disconnected.");
            // Clean up resources if necessary (e.g., cancel AI stream if possible)
            stream.controller.abort(); // Attempt to abort the OpenAI stream
            res.end();
        });

        // Process the stream
        for await (const chunk of stream) {
            const content = chunk.choices[0]?.delta?.content || '';
            if (content) {
                res.write(`data: ${JSON.stringify({ chunk: content })}\n\n`);
            }
        }

        // Signal stream end
        res.write(`data: ${JSON.stringify({ end: true })}\n\n`);
        res.end();
        console.log("[Chat API Stream] Stream finished normally.");

    } catch (error: any) {
        console.error("[Chat API Stream] Error during streaming:", error);
        if (!res.headersSent) {
            // If headers not sent, can still send JSON error
            res.status(500).json({ error: 'Internal Server Error during streaming setup' });
        } else if (!res.writableEnded) {
            // If headers sent but stream not ended, try to send SSE error and end
            try {
                res.write(`data: ${JSON.stringify({ error: `Server error: ${error.message || 'Unknown error'}` })}\n\n`);
            } catch (writeError) {
                console.error("[Chat API Stream] Error writing SSE error message:", writeError);
            } finally {
                res.end();
            }
        }
        // If stream already ended or errored writing, do nothing more
    }
};

router.get('/', handleChatMessageStream); // Changed to GET

export default router; 