import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
// Using react-icons/fi for closer match to screenshot icons
import { FiCornerUpLeft, FiChevronDown, FiLoader, FiRefreshCw } from 'react-icons/fi';
import { motion, AnimatePresence } from 'framer-motion'; // Import animation

// --- New Interfaces matching Backend --- //
interface EmailInfo {
    id: string;
    heading: string;
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

    // Wrap fetch logic in useCallback to avoid recreating it on every render
    const fetchData = useCallback(async (isManualRefresh = false) => {
        // Show loader only on initial load or manual refresh
        if (isManualRefresh || data === null) {
             setLoading(true);
        }
        setError(null);
        try {
            const response = await fetch('http://localhost:3001/api/homescreen_emails');
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
            }
            const result: HomescreenData = await response.json();
            setData(result);
        } catch (err: any) {
            console.error("Fetch error:", err);
            // Don't overwrite existing data with error if background refresh fails
            if (data === null) { 
                 setError(`Failed to fetch dashboard data: ${err.message}. Ensure backend is running and CORS is enabled.`);
            }
        } finally {
            setLoading(false);
        }
    }, [data]); // Depend on `data` so we can avoid full loading state on background refresh

    // Initial fetch
    useEffect(() => {
        fetchData();
    }, [fetchData]); // Use fetchData as dependency

    const handleRefresh = () => {
        fetchData(true); // Pass true to indicate manual refresh
    };

    const getGreeting = (): string => {
        const hour = new Date().getHours();
        if (hour < 12) return "Good morning";
        if (hour < 18) return "Good afternoon";
        return "Good evening";
    };

    if (loading && !data) { // Only show full page loader on initial load
        return <div className="flex justify-center items-center h-64"><FiLoader className="animate-spin h-8 w-8 text-blue-600" /></div>;
    }

    if (error && !data) { // Only show full page error if no data loaded initially
        return <div className="text-red-600 p-4 bg-red-50 border border-red-300 rounded">Error: {error}</div>;
    }

    if (!data) { // Handle case where data is null after initial load attempt (should have error)
        return <div className="text-gray-500">No email data available. Try refreshing.</div>;
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
            {/* Header with Refresh Button */} 
            <div className="flex justify-between items-center">
                <h1 className="text-4xl font-semibold text-gray-800">
                    {getGreeting()},<br />Nick. 
                </h1>
                <button
                    onClick={handleRefresh}
                    className={`p-2 rounded-full hover:bg-gray-100 text-gray-500 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-blue-400 transition-colors ${loading ? 'animate-spin' : ''}`}
                    disabled={loading} // Disable while loading
                    aria-label="Refresh homescreen data"
                >
                    <FiRefreshCw size={20} />
                </button>
            </div>
            
            {/* Display error inline if it happens during refresh */}
            {error && data && (
                <div className="text-red-600 p-3 bg-red-50 border border-red-200 rounded text-sm">Refresh Error: {error}</div>
            )}

            {/* Urgent Emails - Cleaned up display */}
            <section>
                <h2 className={sectionHeaderStyle}>
                    {data.urgent.length > 0
                        ? `You have ${data.urgent.length} urgent ${pluralize(data.urgent.length, 'email', 'emails')} needing attention:`
                        : "No urgent emails identified."
                    }
                </h2>
                {data.urgent.length > 0 && (
                    // Remove bulletPointStyle from ul, add spacing if needed
                    <ul className={`space-y-1`}>
                        {data.urgent.map((email) => (
                            <li key={email.id} className={`${listItemStyle} hover:bg-gray-50 p-1 rounded`}>
                                <Link to={`/email/${email.id}`} className="flex items-center">
                                    <FiCornerUpLeft className="text-blue-500 mr-2 flex-shrink-0" size={16} />
                                    {/* Display only heading, add reasoning as hover title */}
                                    <div title={email.reasoning} className="flex-grow min-w-0">
                                        <span className="font-medium text-gray-800 hover:underline truncate block">{email.heading}</span>
                                    </div>
                                </Link>
                            </li>
                        ))}
                    </ul>
                )}
            </section>

            <hr className="border-gray-200" />

            {/* Delegatable Emails - Cleaned up display */}
            <section>
                 <Disclosure title={`${data.delegate.length} ${pluralize(data.delegate.length, 'email', 'emails')} identified that could potentially be delegated`} headerStyle={sectionHeaderStyle}>
                     {data.delegate.length > 0 ? (
                         // Remove bulletPointStyle from ul, add spacing if needed
                         <ul className={`space-y-1 mt-2`}>
                             {data.delegate.map((email) => (
                                 <li key={email.id} className={`${listItemStyle} hover:bg-gray-50 p-1 rounded`}>
                                     <Link to={`/email/${email.id}`} className="flex items-center">
                                         {/* Use consistent icon */}
                                         <FiCornerUpLeft className="text-blue-500 mr-2 flex-shrink-0" size={16} />
                                         {/* Display only heading, add reasoning as hover title */}
                                         <div title={email.reasoning} className="flex-grow min-w-0">
                                             <span className="font-medium text-gray-800 hover:underline truncate block">{email.heading}</span>
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

            {/* Waiting On Emails - Cleaned up display */}
            <section>
                <Disclosure title={`${data.waiting_on.length} ${pluralize(data.waiting_on.length, 'email', 'emails')} identified where you are waiting for a response`} headerStyle={sectionHeaderStyle}>
                     {data.waiting_on.length > 0 ? (
                         // Remove bulletPointStyle from ul, add spacing if needed
                         <ul className={`space-y-1 mt-2`}>
                             {data.waiting_on.map((email) => (
                                 <li key={email.id} className={`${listItemStyle} hover:bg-gray-50 p-1 rounded`}>
                                     <Link to={`/email/${email.id}`} className="flex items-center">
                                         {/* Use consistent icon */}
                                         <FiCornerUpLeft className="text-blue-500 mr-2 flex-shrink-0" size={16} />
                                         {/* Display only heading, add reasoning as hover title */}
                                         <div title={email.reasoning} className="flex-grow min-w-0">
                                             <span className="font-medium text-gray-800 hover:underline truncate block">{email.heading}</span>
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