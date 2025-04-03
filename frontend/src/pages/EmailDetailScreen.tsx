import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { FiArrowLeft, FiLoader, FiTrash2 } from 'react-icons/fi';

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
    const [isDeleting, setIsDeleting] = useState<boolean>(false);
    const [deleteError, setDeleteError] = useState<string | null>(null);

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

    // --- Delete Handler --- 
    const handleDelete = async () => {
        if (!emailId || isDeleting) return;

        // Optional: Confirmation dialog
        if (!window.confirm("Are you sure you want to delete this email?")) {
            return;
        }

        setIsDeleting(true);
        setDeleteError(null);

        try {
            const response = await fetch(`http://localhost:3001/api/email/${emailId}`, {
                method: 'DELETE',
            });

            const result = await response.json(); // Even if no body, try to parse for potential error messages

            if (!response.ok) {
                throw new Error(result.detail || `HTTP error! status: ${response.status}`);
            }

            console.log(result.message); // Log success message from backend
            // Navigate back to the previous screen (likely the list) upon successful deletion
            navigate(-1); 
            // Optionally: show a success toast/message before navigating

        } catch (err: any) {
            console.error("Delete email error:", err);
            setDeleteError(`Failed to delete email: ${err.message}`);
        } finally {
            setIsDeleting(false);
        }
    };
    // --- End Delete Handler ---

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

            {/* Delete Button Section */}
            <div className="mt-6 pt-4 border-t flex justify-end items-center space-x-4">
                 {deleteError && (
                     <p className="text-sm text-red-600">Error: {deleteError}</p>
                 )}
                <button 
                    onClick={handleDelete}
                    className={`px-4 py-2 rounded-md text-white font-medium transition-colors duration-150 ease-in-out flex items-center ${
                        isDeleting
                        ? 'bg-gray-400 cursor-not-allowed'
                        : 'bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500'
                    }`}
                    disabled={isDeleting}
                >
                     {isDeleting ? (
                        <FiLoader className="animate-spin -ml-1 mr-2 h-5 w-5" />
                     ) : (
                        <FiTrash2 className="-ml-1 mr-2 h-5 w-5" />
                     )}
                    {isDeleting ? 'Deleting...' : 'Delete Email'}
                </button>
            </div>
        </div>
    );
};

export default EmailDetailScreen; 