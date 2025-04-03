import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Link, Outlet } from 'react-router-dom';
import { VscMenu, VscMail, VscArrowUp } from "react-icons/vsc"; // Using VSC icons for now
import { FiChevronLeft } from "react-icons/fi"; // Icon for logo
import ChatOverlay from './ChatOverlay'; // Import the overlay
import { AnimatePresence, motion } from 'framer-motion'; // Import AnimatePresence and motion
import EmailIngestionForm from './EmailIngestionForm'; // Import the ingestion form

// --- Interfaces --- //

// For email references in chat responses
interface EmailRef {
    id: string;
    subject: string;
}

// Message type definition - added optional references
export interface Message {
    id: string;
    sender: 'user' | 'assistant';
    text: string;
    references?: EmailRef[]; // Optional list of email references
}

// Expected structure from /api/email_rag
interface ChatRagApiResponse {
    answer_text: string;
    references: EmailRef[];
}

const MainLayout: React.FC = () => {
    const showNotification = true;
    const [chatInput, setChatInput] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [chatHistory, setChatHistory] = useState<Message[]>([]);
    const [isChatOpen, setIsChatOpen] = useState(false); // State for overlay visibility
    const [currentView, setCurrentView] = useState<'chat' | 'ingest'>('chat'); // State for main view
    const [isMenuOpen, setIsMenuOpen] = useState(false); // State for hamburger menu dropdown
    const menuRef = useRef<HTMLDivElement>(null); // Ref for detecting clicks outside menu

    // Function to close chat and clean up any connections (SSE ref removed)
    const closeChat = useCallback(() => {
        setIsChatOpen(false);
        setIsSubmitting(false); // Ensure submitting state is reset
    }, []);

    const handleChatSubmit = async (event?: React.FormEvent) => {
        event?.preventDefault();
        const messageText = chatInput.trim();
        if (!messageText || isSubmitting) return;

        setIsSubmitting(true);
        setChatInput(''); // Clear input immediately

        // Add user message to history
        const userMessageId = `user-${Date.now()}`;
        setChatHistory(prev => [...prev, { id: userMessageId, sender: 'user', text: messageText }]);

        // Add placeholder for assistant response (non-streaming)
        const assistantMessageId = `assistant-${Date.now()}`;
        setChatHistory(prev => [...prev, { 
            id: assistantMessageId, 
            sender: 'assistant', 
            text: '...' 
            // No references initially
        }]);

        try {
            console.log(`[API] Sending query to /api/email_rag: ${messageText}`);
            const response = await fetch('http://localhost:3001/api/email_rag', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: messageText }),
            });

            if (!response.ok) {
                // Handle HTTP errors (e.g., 4xx, 5xx)
                const errorData = await response.json().catch(() => ({ detail: "Unknown server error" }));
                console.error("[API] Error response:", response.status, errorData);
                throw new Error(errorData.detail || `HTTP error ${response.status}`);
            }

            // Expect structure: { answer_text: string, references: EmailRef[] }
            const result: ChatRagApiResponse = await response.json();
            console.log("[API] Received structured answer:", result);

            // Update the placeholder with the actual response and references
            setChatHistory(prev => prev.map(msg =>
                msg.id === assistantMessageId
                    ? { 
                        ...msg, 
                        text: result.answer_text || "Sorry, I couldn't get a response.", 
                        references: result.references || [] // Add references
                      }
                    : msg
            ));

        } catch (error) {
            console.error("[API] Failed to fetch RAG response:", error);
            // Update the placeholder message to show an error
            setChatHistory(prev => prev.map(msg =>
                msg.id === assistantMessageId
                    ? { ...msg, text: `Error: ${error instanceof Error ? error.message : 'Failed to connect'}` }
                    : msg
            ));
            // Optionally restore input or handle error differently
            // setChatInput(messageText); 
        } finally {
            setIsSubmitting(false); // Re-enable input
        }
    };

    // Add onFocus handler to open chat
    const handleInputFocus = () => {
        setIsChatOpen(true);
    };

    // --- Menu Handling --- 
    const toggleMenu = () => {
        setIsMenuOpen(!isMenuOpen);
    };

    // Close menu if clicked outside
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
                setIsMenuOpen(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
        };
    }, [menuRef]);

    const handleIngestClick = () => {
        setCurrentView('ingest');
        setIsMenuOpen(false); // Close menu after selection
    };
    // --- End Menu Handling ---

    return (
        <div className="flex flex-col h-screen bg-white text-gray-800">
            {/* Top Navigation Bar - removed shadow, adjusted padding */}
            <nav className="bg-white p-4 flex justify-between items-center sticky top-0 z-30 border-b border-gray-200"> {/* Increased z-index slightly */}
                {/* Logo - Sets view back to 'chat' */}
                <button 
                    onClick={() => setCurrentView('chat')} 
                    className="text-blue-600 text-3xl transform -rotate-90 focus:outline-none p-1" // Added padding
                    aria-label="Go to main chat view"
                >
                    <FiChevronLeft />
                </button>
                <div className="flex items-center space-x-4">
                    {/* Mail Icon - Link to /emails */}
                    <Link to="/emails" className="text-gray-600 hover:text-blue-600 relative p-1">
                        <VscMail size={24} />
                        {showNotification && (
                            <span className="absolute top-0 right-0 block h-2 w-2 rounded-full ring-1 ring-white bg-red-500"></span>
                        )}
                    </Link>
                    {/* Hamburger Menu Icon & Dropdown */}
                    <div className="relative" ref={menuRef}>
                        <button 
                            onClick={toggleMenu} 
                            className="text-gray-600 hover:text-blue-600 focus:outline-none p-1" // Added padding
                            aria-label="Open menu"
                            aria-expanded={isMenuOpen}
                        >
                            <VscMenu size={24} />
                        </button>
                        <AnimatePresence>
                            {isMenuOpen && (
                                <motion.div 
                                    initial={{ opacity: 0, y: -10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: -10 }}
                                    transition={{ duration: 0.15 }}
                                    className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg py-1 z-40 border border-gray-200" // Ensure menu is above content
                                >
                                    <button
                                        onClick={handleIngestClick}
                                        className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 hover:text-gray-900 focus:outline-none focus:bg-gray-100"
                                    >
                                        Ingest Emails
                                    </button>
                                    {/* Add other menu items here if needed */}
                                    {/* <Link to="/settings" className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">Settings</Link> */}
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </div>
            </nav>

            {/* Main Content Area - Conditional Rendering */}
            <main className="flex-grow overflow-y-auto p-4 sm:p-6">
                {currentView === 'ingest' ? (
                    <EmailIngestionForm />
                ) : (
                    <Outlet /> // Render the default route content (e.g., HomeScreen)
                )}
            </main>

            {/* Chat Overlay - Wrap in AnimatePresence */}
            <AnimatePresence>
                {isChatOpen && (
                    <ChatOverlay messages={chatHistory} isOpen={isChatOpen} onClose={closeChat} />
                )}
            </AnimatePresence>

            {/* Bottom Input Bar */}
            <footer className="bg-white p-3 sticky bottom-0 z-50 border-t border-gray-200"> { /* Increased z-index */ }
                <form onSubmit={handleChatSubmit} className="relative max-w-3xl mx-auto">
                    <input
                        type="text"
                        placeholder="Ask about your emails..." // Updated placeholder
                        value={chatInput}
                        onChange={(e) => setChatInput(e.target.value)}
                        onFocus={handleInputFocus}
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