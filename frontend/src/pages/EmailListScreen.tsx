import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { FiLoader, FiMail, FiChevronRight } from 'react-icons/fi';

// Interface for the email list item data expected from the API
interface EmailListItem {
    id: string;
    sender: string;
    subject: string;
    received_date: string;
}

// Interface for the API response
interface AllEmailsResponse {
    emails: EmailListItem[];
}

const EmailListScreen: React.FC = () => {
    const [emails, setEmails] = useState<EmailListItem[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchEmails = async () => {
            setLoading(true);
            setError(null);
            try {
                const response = await fetch('http://localhost:3001/api/emails');
                if (!response.ok) {
                    const errorText = await response.text();
                    throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
                }
                const result: AllEmailsResponse = await response.json();
                // Sort emails by date, newest first
                const sortedEmails = result.emails.sort((a, b) => 
                    new Date(b.received_date).getTime() - new Date(a.received_date).getTime()
                );
                setEmails(sortedEmails);
            } catch (err: any) {
                console.error("Fetch emails error:", err);
                setError(`Failed to fetch emails: ${err.message}`);
            } finally {
                setLoading(false);
            }
        };

        fetchEmails();
    }, []); // Runs once on mount

    // Function to format the date briefly (e.g., "Apr 3" or "10:30")
    const formatBriefDate = (isoDate: string): string => {
        try {
            const date = new Date(isoDate);
            const now = new Date();
            const isToday = date.toDateString() === now.toDateString();

            if (isToday) {
                // Format as HH:MM
                return date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', hour12: false });
            } else {
                // Format as Mon Day (e.g., Apr 3)
                return date.toLocaleDateString('en-GB', { month: 'short', day: 'numeric' });
            }
        } catch {
            return ""; // Return empty on error
        }
    };

    if (loading) {
        return <div className="flex justify-center items-center h-64"><FiLoader className="animate-spin h-8 w-8 text-blue-600" /></div>;
    }

    if (error) {
        return <div className="p-4 max-w-3xl mx-auto text-red-600 bg-red-50 border border-red-300 rounded">Error: {error}</div>;
    }

    return (
        <div className="p-4 max-w-3xl mx-auto">
            <h1 className="text-2xl font-semibold text-gray-800 mb-4">All Emails</h1>
            {emails.length === 0 ? (
                <p className="text-gray-500">No emails found.</p>
            ) : (
                <ul className="divide-y divide-gray-200">
                    {emails.map(email => (
                        <li key={email.id} className="py-3 hover:bg-gray-50">
                            <Link to={`/email/${email.id}`} className="flex items-center justify-between text-sm">
                                <div className="flex items-center min-w-0">
                                    {/* Placeholder Icon - could be initial or avatar */}
                                    <div className="flex-shrink-0 h-8 w-8 rounded-full bg-gray-300 flex items-center justify-center mr-3">
                                        <FiMail className="h-4 w-4 text-gray-500" />
                                    </div>
                                    <div className="min-w-0 flex-1">
                                        <p className="font-medium text-gray-800 truncate">{email.sender}</p>
                                        <p className="text-gray-600 truncate">{email.subject}</p>
                                    </div>
                                </div>
                                <div className="ml-2 flex-shrink-0 flex flex-col items-end">
                                     <span className="text-xs text-gray-500">{formatBriefDate(email.received_date)}</span>
                                     <FiChevronRight className="h-5 w-5 text-gray-400 mt-1" />
                                </div>
                            </Link>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
};

export default EmailListScreen; 