import React from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { FiExternalLink } from 'react-icons/fi';
import { Message } from './MainLayout';

interface ChatMessageProps {
    sender: 'user' | 'assistant';
    text: string;
    references?: Message['references'];
    onClose?: () => void;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ sender, text, references, onClose }) => {
    const isUser = sender === 'user';

    // Styling based on sender
    const baseClasses = "max-w-[75%] w-fit px-4 py-2 rounded-lg text-sm mb-2";
    const userClasses = `ml-auto bg-user-message-bg text-gray-800 shadow-sm`;
    const assistantClasses = `text-gray-800`;

    const containerClasses = `${baseClasses} ${isUser ? userClasses : assistantClasses}`;

    // Animation variants for pop-in effect
    const messageVariants = {
        hidden: { opacity: 0, y: 10 },
        visible: { opacity: 1, y: 0, transition: { duration: 0.3, ease: "easeOut" } }
    };

    const renderContent = () => (
        <div className={containerClasses}>
            <p className="whitespace-pre-wrap">{text}</p>
            
            {!isUser && references && references.length > 0 && (
                <div className="mt-2 pt-2 border-t border-gray-200 space-y-1">
                    <p className="text-xs font-medium text-gray-500">Referenced Emails:</p>
                    <ul className="list-none pl-0 space-y-1">
                        {references.map((ref) => (
                            <li key={ref.id} className="text-xs">
                                <Link 
                                    to={`/email/${ref.id}`}
                                    className="inline-flex items-center text-blue-600 hover:text-blue-800 hover:underline"
                                    onClick={onClose}
                                >
                                    <FiExternalLink className="mr-1 flex-shrink-0" size={12}/>
                                    <span className="truncate">{ref.subject || `Email ID: ${ref.id}`}</span> 
                                </Link>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );

    // Only animate user messages
    if (isUser) {
        return (
            <motion.div
                className="w-full flex"
                variants={messageVariants}
                initial="hidden"
                animate="visible"
            >
                {renderContent()}
            </motion.div>
        );
    }

    // Render assistant messages (potentially with references) without motion wrapper
    return renderContent();
};

export default ChatMessage;
