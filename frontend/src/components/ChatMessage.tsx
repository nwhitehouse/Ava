import React from 'react';

interface ChatMessageProps {
    sender: 'user' | 'assistant';
    text: string;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ sender, text }) => {
    const isUser = sender === 'user';

    // Styling based on sender
    const baseClasses = "max-w-[75%] w-fit px-4 py-2 rounded-lg shadow-sm text-sm";
    const userClasses = "ml-auto bg-user-message-bg text-gray-800"; // User: Custom bg, dark text, right-aligned
    const assistantClasses = "text-gray-800"; // Assistant: No background, dark text, left-aligned

    const containerClasses = `${"" /* Base styles */} ${baseClasses} ${isUser ? userClasses : assistantClasses}`;

    return (
        <div className={containerClasses}>
            {/* Render text, handling potential newlines */}
            <p className="whitespace-pre-wrap">{text}</p>
        </div>
    );
};

export default ChatMessage;
