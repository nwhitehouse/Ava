import React, { useRef, useEffect } from 'react';
import ChatMessage from './ChatMessage';
import { Message } from './MainLayout'; // Import Message type
import { FiChevronDown } from "react-icons/fi"; // Icon for minimize
import { motion, AnimatePresence } from 'framer-motion'; // Import animation components

interface ChatOverlayProps {
    messages: Message[];
    isOpen: boolean;
    onClose: () => void; // Function to close/minimize the overlay
}

const ChatOverlay: React.FC<ChatOverlayProps> = ({ messages, isOpen, onClose }) => {
    const messagesEndRef = useRef<HTMLDivElement>(null); // Ref to the end div

    // Scroll to bottom when messages change
    useEffect(() => {
        // Use scrollIntoView on the ref at the end of the messages
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]); // Rerun whenever messages array changes

    // Overlay animation variants (slide up/down)
    const overlayVariants = {
        hidden: { y: "100%", opacity: 0 },
        visible: { y: 0, opacity: 1, transition: { duration: 0.4, ease: "easeInOut" } },
        exit: { y: "100%", opacity: 0, transition: { duration: 0.3, ease: "easeInOut" } }
    };

    // Don't render anything if not open
    // AnimatePresence handles the exit animation
    if (!isOpen) return null;

    return (
        <motion.div
            key="chat-overlay" // Key for AnimatePresence
            className="fixed inset-0 z-40 bg-white flex flex-col h-full"
            variants={overlayVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
        >
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

            {/* Message Container */}
            {/* Make sure this container itself allows scrolling */}
            <div className="flex-grow overflow-y-auto p-6 flex flex-col">
                {/* Remove the AnimatePresence and motion.div wrapper around each message */}
                {messages.map((msg) => (
                    <div key={msg.id} className="mb-10">
                        <ChatMessage sender={msg.sender} text={msg.text} />
                    </div>
                ))}
                {/* Empty div at the end to ensure scrollIntoView works */}
                <div ref={messagesEndRef} />
            </div>
        </motion.div>
    );
};

export default ChatOverlay;