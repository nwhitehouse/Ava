import React from 'react';
import ChatMessage from './ChatMessage';
import { Message } from './MainLayout'; // Import Message type from MainLayout

interface ChatDisplayProps {
    messages: Message[];
}

const ChatDisplay: React.FC<ChatDisplayProps> = ({ messages }) => {
    return (
        // Container for chat messages
        // Add some spacing between messages
        <div className="space-y-4 mb-4">
            {messages.map((msg) => (
                <ChatMessage key={msg.id} sender={msg.sender} text={msg.text} />
            ))}
        </div>
    );
};

export default ChatDisplay; 