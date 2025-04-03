import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
// Using react-icons/fi for closer match to screenshot icons
import { FiCornerUpLeft, FiChevronDown, FiLoader } from 'react-icons/fi';
import { motion, AnimatePresence } from 'framer-motion'; // Import animation

// --- New Interfaces matching Backend --- //
interface EmailInfo {
    id: string;
    subject: string;
    sender: string;
    reasoning: string;
    // Note: We don't have a unique ID from the backend model currently,
    // so we'll use subject+sender for keys, which might not be ideal if duplicates exist.
}

interface HomescreenData {
    urgent: EmailInfo[];
    delegate: EmailInfo[];
    waiting_on: EmailInfo[];
}

// --- Removed Old Interfaces --- //
// interface Email { ... }
// interface WaitingPerson { ... }
// interface Meeting { ... }
// interface DashboardData { ... }

const HomeScreen: React.FC = () => {
    // Use the new interface for state
    const [data, setData] = useState<HomescreenData | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            setError(null);
            try {
                // Fetch from the new homescreen endpoint
                const response = await fetch('http://localhost:3001/api/homescreen_emails');
                if (!response.ok) {
                    const errorText = await response.text(); // Get error details if available
                    throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
                }
                // Expect data in the HomescreenData structure
                const result: HomescreenData = await response.json();
                setData(result);
            } catch (err: any) {
                console.error("Fetch error:", err);
                setError(`Failed to fetch dashboard data: ${err.message}. Ensure backend is running and CORS is enabled.`);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    const getGreeting = (): string => {
        const hour = new Date().getHours();
        if (hour < 12) return "Good morning";
        if (hour < 18) return "Good afternoon";
        return "Good evening";
    };

    if (loading) {
        return <div className="flex justify-center items-center h-64"><FiLoader className="animate-spin h-8 w-8 text-blue-600" /></div>;
    }

    if (error) {
        return <div className="text-red-600 p-4 bg-red-50 border border-red-300 rounded">Error: {error}</div>;
    }

    // Handle case where data might be null or missing categories (though backend defaults to empty lists)
    if (!data || !data.urgent || !data.delegate || !data.waiting_on) {
        return <div className="text-gray-500">No email data available or data is incomplete.</div>;
    }

    const pluralize = (count: number, singular: string, plural: string): string => {
        return count === 1 ? singular : plural;
    };

    const sectionHeaderStyle = "text-base font-bold text-gray-700 mb-3";
    const listItemStyle = "text-sm text-gray-600";
    // Removed linkStyle as we don't have email IDs to link to currently
    const bulletPointStyle = "list-disc list-inside ml-1";

    return (
        <div className="space-y-6 max-w-3xl mx-auto">
            {/* Updated Greeting - no user name */}
            <h1 className="text-4xl font-semibold text-gray-800">
                {getGreeting()}.
            </h1>

            {/* Urgent Emails - Updated structure with Links */}
            <section>
                <h2 className={sectionHeaderStyle}>
                    {data.urgent.length > 0
                        ? `You have ${data.urgent.length} urgent ${pluralize(data.urgent.length, 'email', 'emails')} needing attention:`
                        : "No urgent emails identified."
                    }
                </h2>
                {data.urgent.length > 0 && (
                    <ul className={`space-y-1.5 ${bulletPointStyle}`}>
                        {data.urgent.map((email) => (
                            // Use email.id for the key and link
                            <li key={email.id} className={`${listItemStyle} hover:bg-gray-50 p-1 rounded`}>
                                <Link to={`/email/${email.id}`} className="flex items-start">
                                    <FiCornerUpLeft className="text-red-500 mr-2 mt-0.5 flex-shrink-0" size={14} />
                                    <div>
                                        <span className="font-medium text-gray-800 hover:underline">{email.subject}</span> from <span className="font-medium">{email.sender}</span>
                                        <p className="text-xs text-gray-500 pl-4">Reasoning: {email.reasoning}</p>
                                    </div>
                                </Link>
                            </li>
                        ))}
                    </ul>
                )}
            </section>

            <hr className="border-gray-200" />

            {/* Delegatable Emails - Updated structure with Links */}
            <section>
                 <Disclosure title={`${data.delegate.length} ${pluralize(data.delegate.length, 'email', 'emails')} identified that could potentially be delegated`} headerStyle={sectionHeaderStyle}>
                     {data.delegate.length > 0 ? (
                         <ul className={`space-y-1.5 ${bulletPointStyle} mt-2`}>
                             {data.delegate.map((email) => (
                                 <li key={email.id} className={`${listItemStyle} hover:bg-gray-50 p-1 rounded`}>
                                     <Link to={`/email/${email.id}`} className="flex items-start">
                                         <span className="mr-2 mt-0.5">•</span>
                                         <div>
                                             <span className="font-medium text-gray-800 hover:underline">{email.subject}</span> from <span className="font-medium">{email.sender}</span>
                                             <p className="text-xs text-gray-500 pl-4">Reasoning: {email.reasoning}</p>
                                         </div>
                                     </Link>
                                 </li>
                             ))}
                         </ul>
                     ) : (
                         <p className={`${listItemStyle} mt-2`}>No specific emails identified for delegation based on current context.</p>
                     )}
                </Disclosure>
            </section>

            <hr className="border-gray-200" />

            {/* Waiting On Emails - Updated structure with Links */}
            <section>
                <Disclosure title={`${data.waiting_on.length} ${pluralize(data.waiting_on.length, 'email', 'emails')} identified where you are waiting for a response`} headerStyle={sectionHeaderStyle}>
                     {data.waiting_on.length > 0 ? (
                         <ul className={`space-y-1.5 ${bulletPointStyle} mt-2`}>
                             {data.waiting_on.map((email) => (
                                 <li key={email.id} className={`${listItemStyle} hover:bg-gray-50 p-1 rounded`}>
                                     <Link to={`/email/${email.id}`} className="flex items-start">
                                         <span className="mr-2 mt-0.5">•</span>
                                         <div>
                                             <span className="font-medium text-gray-800 hover:underline">{email.subject}</span> from <span className="font-medium">{email.sender}</span>
                                             <p className="text-xs text-gray-500 pl-4">Reasoning: {email.reasoning}</p>
                                         </div>
                                     </Link>
                                 </li>
                            ))}
                         </ul>
                     ) : (
                         <p className={`${listItemStyle} mt-2`}>No specific emails identified where you are waiting for info based on current context.</p>
                     )}
                 </Disclosure>
            </section>

             {/* Removed Meetings Section */}

        </div>
    );
};

// Simple Disclosure/Accordion Component - unchanged
interface DisclosureProps {
    title: string;
    children: React.ReactNode;
    headerStyle?: string; // Optional style prop
}

const Disclosure: React.FC<DisclosureProps> = ({ title, children, headerStyle }) => {
    const [isOpen, setIsOpen] = useState(false);
    const defaultHeaderStyle = "text-base font-bold text-gray-700 mb-3";
    const contentVariants = {
        collapsed: { height: 0, opacity: 0, transition: { duration: 0.3, ease: "easeInOut" } },
        open: { height: "auto", opacity: 1, transition: { duration: 0.3, ease: "easeInOut" } }
    };
    return (
        <div>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className={`flex justify-between items-center w-full text-left ${headerStyle || defaultHeaderStyle}`}
                aria-expanded={isOpen}
            >
                <span>{title}</span>
                <motion.div animate={{ rotate: isOpen ? 180 : 0 }} transition={{ duration: 0.3 }}>
                    <FiChevronDown className="text-gray-500" />
                </motion.div>
            </button>
            <AnimatePresence initial={false}>
                {isOpen && (
                    <motion.div
                        key="content"
                        initial="collapsed"
                        animate="open"
                        exit="collapsed"
                        variants={contentVariants}
                        style={{ overflow: 'hidden' }}
                    >
                        {children}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default HomeScreen; 