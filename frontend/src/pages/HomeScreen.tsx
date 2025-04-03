import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
// Using react-icons/fi for closer match to screenshot icons
import { FiCornerUpLeft, FiChevronDown, FiLoader } from 'react-icons/fi';

// Define interfaces for the data structure
interface Email {
    id: string;
    sender: string;
    subject: string;
    snippet: string;
}

interface WaitingPerson {
    id: string;
    name: string;
    topic: string;
}

interface Meeting {
    id: string;
    title: string;
    time: string;
}

interface DashboardData {
    userName: string;
    urgentEmails: Email[];
    delegatableEmails: Email[];
    waitingFor: WaitingPerson[];
    meetingsToPrep: Meeting[];
}

const HomeScreen: React.FC = () => {
    const [data, setData] = useState<DashboardData | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            setError(null);
            try {
                // NOTE: Assumes backend runs on port 3001
                // We'll need CORS enabled on the backend for this to work from the frontend dev server
                const response = await fetch('http://localhost:3001/api/mock/dashboard');
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const result: DashboardData = await response.json();
                setData(result);
            } catch (err: any) {
                console.error("Fetch error:", err);
                setError(`Failed to fetch dashboard data: ${err.message}. Ensure backend is running and CORS is enabled.`);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, []); // Empty dependency array means this runs once on mount

    // Function to get time-based greeting
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

    if (!data) {
        return <div className="text-gray-500">No data available.</div>;
    }

    // Helper function for simple pluralization
    const pluralize = (count: number, singular: string, plural: string): string => {
        return count === 1 ? singular : plural;
    };

    // Consistent text styling
    const sectionHeaderStyle = "text-base font-bold text-gray-700 mb-3"; // Updated weight
    const listItemStyle = "text-sm text-gray-600"; // Smaller text for list items
    const linkStyle = "hover:underline text-gray-800"; // Default link style
    const bulletPointStyle = "list-disc list-inside ml-1"; // Simple bullet point

    return (
        <div className="space-y-6 max-w-3xl mx-auto"> { /* Constrain width */ }
            <h1 className="text-4xl font-semibold text-gray-800">
                {getGreeting()},<br />{data.userName}.
            </h1>

            {/* Urgent Emails */}
            <section>
                <h2 className={sectionHeaderStyle}>
                    You have {data.urgentEmails.length} {pluralize(data.urgentEmails.length, 'email', 'emails')} that need a response from you ASAP.
                </h2>
                <ul className={`space-y-1.5 ${bulletPointStyle}`}>
                    {data.urgentEmails.map(email => (
                        <li key={email.id} className={`${listItemStyle} flex items-start`}>
                            <FiCornerUpLeft className="text-blue-500 mr-2 mt-0.5 flex-shrink-0" size={14} />
                            <Link to={`/email/${email.id}`} className={linkStyle}>
                                <span className="font-medium">{email.sender}</span> needs you to <span className="font-medium">{email.subject}</span>.
                            </Link>
                        </li>
                    ))}
                </ul>
            </section>

            <hr className="border-gray-200" />

            {/* Delegatable Emails */}
            <section>
                 <Disclosure title={`You have ${data.delegatableEmails.length} ${pluralize(data.delegatableEmails.length, 'email', 'emails')} that I can delegate for you`} headerStyle={sectionHeaderStyle}>
                     <ul className={`space-y-1.5 ${bulletPointStyle} mt-2`}>
                        {data.delegatableEmails.map(email => (
                            <li key={email.id} className={`${listItemStyle} flex items-start`}>
                                <span className="mr-2 mt-0.5">•</span>
                                <Link to={`/email/${email.id}`} className={linkStyle}>
                                   <span className="font-medium">{email.sender}</span> - <span className="italic">{email.subject}</span>
                                </Link>
                            </li>
                        ))}
                    </ul>
                </Disclosure>
            </section>

            <hr className="border-gray-200" />

            {/* Waiting For */}
            <section>
                <Disclosure title={`You are waiting on info from ${data.waitingFor.length} people. I can chase them up`} headerStyle={sectionHeaderStyle}>
                     <ul className={`space-y-1.5 ${bulletPointStyle} mt-2`}>
                        {data.waitingFor.map(person => (
                            <li key={person.id} className={`${listItemStyle} flex items-start`}>
                                <span className="mr-2 mt-0.5">•</span>
                                <div>
                                    <span className="font-medium">{person.name}</span> - <span className="italic">{person.topic}</span>
                                </div>
                            </li>
                        ))}
                    </ul>
                </Disclosure>
            </section>

            <hr className="border-gray-200" />

            {/* Meetings to Prep */}
            <section>
                <Disclosure title={`You need to prep for ${data.meetingsToPrep.length} meetings this week. I can book out time for this`} headerStyle={sectionHeaderStyle}>
                    <ul className={`space-y-1.5 ${bulletPointStyle} mt-2`}>
                        {data.meetingsToPrep.map(meeting => (
                            <li key={meeting.id} className={`${listItemStyle} flex items-start`}>
                                <span className="mr-2 mt-0.5">•</span>
                                <div>
                                    <span className="font-medium">{meeting.title}</span> - <span className="italic">{meeting.time}</span>
                                </div>
                            </li>
                        ))}
                    </ul>
                 </Disclosure>
            </section>
        </div>
    );
};

// Simple Disclosure/Accordion Component - accept headerStyle prop
interface DisclosureProps {
    title: string;
    children: React.ReactNode;
    headerStyle?: string; // Optional style prop
}

const Disclosure: React.FC<DisclosureProps> = ({ title, children, headerStyle }) => {
    const [isOpen, setIsOpen] = useState(false);
    const defaultHeaderStyle = "text-base font-bold text-gray-700 mb-3"; // Updated default weight

    return (
        <div>
            <button
                onClick={() => setIsOpen(!isOpen)}
                // Apply passed style or default, adjust text size/weight
                className={`flex justify-between items-center w-full text-left ${headerStyle || defaultHeaderStyle}`}
            >
                <span>{title}</span>
                 {/* Use FiChevronDown, adjust size and color */}
                <FiChevronDown
                    size={20}
                    className={`text-blue-500 transform transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
                />
            </button>
            {isOpen && (
                // Remove border and padding, rely on list styling
                <div className="mt-1">
                    {children}
                </div>
            )}
        </div>
    );
};

export default HomeScreen; 