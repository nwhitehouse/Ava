import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Link, Outlet } from 'react-router-dom';
import { VscMenu, VscMail, VscArrowUp } from "react-icons/vsc"; // Using VSC icons for now
import { FiChevronLeft } from "react-icons/fi"; // Icon for logo
import ChatOverlay from './ChatOverlay'; // Import the overlay

// Message type definition
export interface Message {
    id: string; // Use string IDs for potential future needs
    sender: 'user' | 'assistant';
    text: string;
    isStreaming?: boolean; // Flag for streaming state
}

const MainLayout: React.FC = () => {
    const showNotification = true;
    const [chatInput, setChatInput] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [chatHistory, setChatHistory] = useState<Message[]>([]);
    const [isChatOpen, setIsChatOpen] = useState(false); // State for overlay visibility
    const eventSourceRef = useRef<EventSource | null>(null); // Ref for SSE connection

    // Function to close chat and clean up SSE connection
    const closeChat = useCallback(() => {
        setIsChatOpen(false);
        if (eventSourceRef.current) {
            console.log("[SSE] Closing EventSource connection.");
            eventSourceRef.current.close();
            eventSourceRef.current = null;
        }
        setIsSubmitting(false); // Ensure submitting state is reset
    }, []);

    const handleChatSubmit = async (event?: React.FormEvent) => {
        event?.preventDefault(); // Prevent default if called from form
        const messageText = chatInput.trim();
        if (!messageText || isSubmitting) return;

        setIsSubmitting(true);
        setIsChatOpen(true); // Open chat overlay ON SUBMIT
        const originalMessage = chatInput;
        setChatInput('');

        // Add user message
        const userMessageId = `user-${Date.now()}`;
        setChatHistory(prev => [...prev, { id: userMessageId, sender: 'user', text: messageText }]);

        // Close existing SSE connection if any
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
        }

        // Add placeholder for assistant message
        const assistantMessageId = `assistant-${Date.now()}`;
        setChatHistory(prev => [...prev, { id: assistantMessageId, sender: 'assistant', text: '', isStreaming: true }]);

        console.log("[SSE] Initializing EventSource...");
        // Initiate SSE connection
        eventSourceRef.current = new EventSource(`http://localhost:3001/api/chat?message=${encodeURIComponent(messageText)}`);

        eventSourceRef.current.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                if (data.chunk) {
                    // Update the streaming message text
                    setChatHistory(prev => prev.map(msg =>
                        msg.id === assistantMessageId
                            ? { ...msg, text: msg.text + data.chunk }
                            : msg
                    ));
                }

                if (data.end) {
                    console.log("[SSE] Stream ended by server.");
                    // Mark streaming as complete
                    setChatHistory(prev => prev.map(msg =>
                        msg.id === assistantMessageId
                            ? { ...msg, isStreaming: false }
                            : msg
                    ));
                    eventSourceRef.current?.close(); // Close connection after server signals end
                    eventSourceRef.current = null;
                    setIsSubmitting(false);
                }

                if (data.error) { // Handle explicit error message from stream
                    console.error("[SSE] Error message from server:", data.error);
                    setChatHistory(prev => prev.map(msg =>
                        msg.id === assistantMessageId
                            ? { ...msg, text: `Error: ${data.error}`, isStreaming: false }
                            : msg
                    ));
                    closeChat();
                }
            } catch (parseError) {
                console.error("[SSE] Error parsing message data:", parseError, "Raw data:", event.data);
                // Update UI to show generic parse error
                setChatHistory(prev => prev.map(msg =>
                    msg.id === assistantMessageId
                        ? { ...msg, text: `${msg.text}\n\nError: Could not parse response.`, isStreaming: false }
                        : msg
                ));
                closeChat();
            }
        };

        eventSourceRef.current.onerror = (error) => {
            console.error("[SSE] EventSource failed:", error);
            setChatHistory(prev => prev.map(msg =>
                 msg.id === assistantMessageId
                    ? { ...msg, text: `${msg.text}\n\nError: Connection failed.`, isStreaming: false }
                    : msg
            ));
            closeChat();
            setChatInput(originalMessage); // Restore input on error
        };
    };

    return (
        <div className="flex flex-col h-screen bg-white text-gray-800">
            {/* Top Navigation Bar - removed shadow, adjusted padding */}
            <nav className="bg-white p-4 flex justify-between items-center sticky top-0 z-10 border-b border-gray-200">
                {/* Logo - Using chevron left rotated */}
                <Link to="/" className="text-blue-600 text-3xl transform -rotate-90">
                    <FiChevronLeft />
                </Link>
                <div className="flex items-center space-x-4">
                    {/* Mail Icon - adjusted color, added notification */}
                    <button className="text-gray-600 hover:text-blue-600 relative">
                        <VscMail size={24} />
                        {showNotification && (
                            <span className="absolute top-0 right-0 block h-2 w-2 rounded-full ring-1 ring-white bg-red-500"></span>
                        )}
                    </button>
                    {/* Menu Icon - adjusted color */}
                    <button className="text-gray-600 hover:text-blue-600">
                        <VscMenu size={24} />
                    </button>
                </div>
            </nav>

            {/* Main Content Area */}
            <main className="flex-grow overflow-y-auto p-6">
                <Outlet />
            </main>

            {/* Chat Overlay - Pass history directly */}
            <ChatOverlay messages={chatHistory} isOpen={isChatOpen} onClose={closeChat} />

            {/* Bottom Input Bar */}
            <footer className="bg-white p-3 sticky bottom-0 z-50 border-t border-gray-200"> { /* Increased z-index */ }
                <form onSubmit={handleChatSubmit} className="relative max-w-3xl mx-auto">
                    <input
                        type="text"
                        placeholder="How can I help?"
                        value={chatInput}
                        onChange={(e) => setChatInput(e.target.value)}
                        disabled={isSubmitting}
                        className="w-full py-2 px-4 pr-12 border border-gray-300 rounded-full bg-white text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                    />
                    <button
                        type="submit"
                        className="absolute right-1.5 top-1/2 transform -translate-y-1/2 bg-blue-600 hover:bg-blue-700 text-white w-8 h-8 flex items-center justify-center rounded-full disabled:opacity-50 disabled:cursor-not-allowed"
                        disabled={!chatInput.trim() || isSubmitting}
                    >
                        <VscArrowUp size={18} />
                    </button>
                </form>
            </footer>
        </div>
    );
};

export default MainLayout; 