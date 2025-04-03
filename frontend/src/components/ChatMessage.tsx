import React from 'react';
import { motion } from 'framer-motion';

interface ChatMessageProps {
    sender: 'user' | 'assistant';
    text: string;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ sender, text }) => {
    const isUser = sender === 'user';

    // Styling based on sender
    const baseClasses = "max-w-[75%] w-fit px-4 py-2 rounded-lg text-sm";
    const userClasses = `ml-auto bg-user-message-bg text-gray-800 shadow-sm`;
    const assistantClasses = `text-gray-800`;

    const containerClasses = `${baseClasses} ${isUser ? userClasses : assistantClasses}`;

    // Animation variants for pop-in effect
    const messageVariants = {
        hidden: { opacity: 0, y: 10 },
        visible: { opacity: 1, y: 0, transition: { duration: 0.3, ease: "easeOut" } }
    };

    // Only animate user messages
    if (isUser) {
        return (
            <motion.div
                className={containerClasses}
                variants={messageVariants}
                initial="hidden"
                animate="visible"
                // No exit needed if parent AnimatePresence handles it
            >
                <p className="whitespace-pre-wrap">{text}</p>
            </motion.div>
        );
    }

    // Render assistant messages without motion wrapper
    return (
        <div className={containerClasses}>
            <p className="whitespace-pre-wrap">{text}</p>
        </div>
    );
};

export default ChatMessage;
