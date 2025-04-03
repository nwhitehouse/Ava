import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { FiArrowLeft, FiLoader } from 'react-icons/fi';

// Interface for the detailed email data expected from the API
interface EmailDetails {
    id: string;
    sender: string;
    subject: string;
    body: string;
    received_date: string;
}

const EmailDetailScreen: React.FC = () => {
    const { emailId } = useParams<{ emailId: string }>();
    const navigate = useNavigate();
    const [email, setEmail] = useState<EmailDetails | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchEmail = async () => {
            if (!emailId) {
                setError("Email ID not provided.");
                setLoading(false);
                return;
            }
            setLoading(true);
            setError(null);
            try {
                const response = await fetch(`http://localhost:3001/api/email/${emailId}`);
                if (!response.ok) {
                    if (response.status === 404) {
                        throw new Error("Email not found.");
                    }
                    const errorText = await response.text();
                    throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
                }
                const result: EmailDetails = await response.json();
                setEmail(result);
            } catch (err: any) {
                console.error("Fetch email error:", err);
                setError(`Failed to fetch email: ${err.message}`);
            } finally {
                setLoading(false);
            }
        };

        fetchEmail();
    }, [emailId]); // Re-fetch if emailId changes

    // Function to format the date nicely
    const formatDate = (isoDate: string): string => {
        try {
            const date = new Date(isoDate);
            // Example format: Wed 25th 09:00
            const options: Intl.DateTimeFormatOptions = {
                weekday: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                hour12: false
            };
            // Basic ordinal suffix handling
            const day = date.getDate();
            let suffix = 'th';
            if (day === 1 || day === 21 || day === 31) suffix = 'st';
            else if (day === 2 || day === 22) suffix = 'nd';
            else if (day === 3 || day === 23) suffix = 'rd';
            
            const formattedDate = date.toLocaleDateString('en-GB', options).replace(/\d{1,2}(?:st|nd|rd|th)?/, `${day}${suffix}`);
            // Adjust format slightly to match screenshot (approximation)
            return formattedDate.replace(',', '').replace(' at ', ' '); 
        } catch {
            return isoDate; // Fallback to ISO string on error
        }
    };

    const goBack = () => {
        navigate(-1); // Go back to the previous page in history
    };

    if (loading) {
        return <div className="flex justify-center items-center h-64"><FiLoader className="animate-spin h-8 w-8 text-blue-600" /></div>;
    }

    if (error) {
        return (
            <div className="p-4 max-w-3xl mx-auto">
                 <button onClick={goBack} className="mb-4 text-blue-600 hover:text-blue-800 flex items-center">
                    <FiArrowLeft className="mr-1" /> Back
                </button>
                <div className="text-red-600 p-4 bg-red-50 border border-red-300 rounded">Error: {error}</div>
            </div>
        );
    }

    if (!email) {
        return (
             <div className="p-4 max-w-3xl mx-auto">
                <button onClick={goBack} className="mb-4 text-blue-600 hover:text-blue-800 flex items-center">
                    <FiArrowLeft className="mr-1" /> Back
                </button>
                <div className="text-gray-500">Email data not available.</div>
            </div>
        );
    }

    // Basic rendering matching the screenshot structure
    return (
        <div className="p-4 max-w-3xl mx-auto space-y-4">
            <button onClick={goBack} className="text-blue-600 hover:text-blue-800 flex items-center mb-2">
                <FiArrowLeft className="mr-1" /> 
            </button>

            <h1 className="text-2xl font-semibold text-gray-800">{email.subject}</h1>
            <div className="text-sm text-gray-600">
                <p>From: {email.sender}</p>
                <p>Received: {formatDate(email.received_date)}</p>
            </div>

            {/* Summary Placeholder */}
            <div className="bg-blue-50 p-3 rounded-lg text-sm text-gray-700 border border-blue-100">
                This is a summary of the email thread and a readout of any actions you need to take. (Placeholder - can be generated later)
            </div>

            {/* Email Body */}
            {/* Using whitespace-pre-wrap to respect newlines from the text */}
            <div className="text-gray-800 text-sm whitespace-pre-wrap">
                {email.body}
            </div>
        </div>
    );
};

export default EmailDetailScreen; 