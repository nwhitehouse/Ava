import React, { useRef, useEffect } from 'react';
import ChatMessage from './ChatMessage';
import { Message } from './MainLayout'; // Import Message type
import { FiChevronDown } from "react-icons/fi"; // Icon for minimize

interface ChatOverlayProps {
    messages: Message[];
    isOpen: boolean;
    onClose: () => void; // Function to close/minimize the overlay
}

const ChatOverlay: React.FC<ChatOverlayProps> = ({ messages, isOpen, onClose }) => {
    const messagesContainerRef = useRef<HTMLDivElement>(null); // Ref to container for scrolling
    const messagesEndRef = useRef<HTMLDivElement>(null); // Ref to the end div

    // Scroll to bottom when messages change
    useEffect(() => {
        // We need a slight delay to allow the DOM to update before scrolling
        const timer = setTimeout(() => {
            if (messagesContainerRef.current) {
                messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
            }
            // Alternative using scrollIntoView on the end ref:
            // messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
        }, 50); // Small delay like 50ms often helps

        return () => clearTimeout(timer); // Cleanup timer on unmount or dependency change
    }, [messages]);

    if (!isOpen) return null;

    return (
        // Full screen white overlay
        <div className="fixed inset-0 z-40 bg-white flex flex-col h-full">
            {/* Header with Minimize Button */}
            <div className="flex justify-end p-4 border-b border-gray-200">
                <button
                    onClick={onClose}
                    className="text-gray-500 hover:text-gray-800 p-1 rounded-full hover:bg-gray-100"
                    aria-label="Minimize chat"
                >
                    <FiChevronDown size={24} />
                </button>
            </div>

            {/* Message Container - normal flow (flex-col), scrolls */}
            <div ref={messagesContainerRef} className="flex-grow overflow-y-auto p-6 flex flex-col">
                {/* Map messages in normal order */}
                {messages.map((msg) => (
                    <div key={msg.id} className="mb-4">
                        <ChatMessage sender={msg.sender} text={msg.text} />
                    </div>
                ))}
                {/* Empty div at the end to scroll to */}
                <div ref={messagesEndRef} />
            </div>
        </div>
    );
};

export default ChatOverlay;