import React, { useState } from 'react';

const EmailIngestionForm: React.FC = () => {
  const [bulkEmailsText, setBulkEmailsText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFeedback(null);

    if (!bulkEmailsText.trim()) {
      setFeedback({ type: 'error', message: 'Email text cannot be empty.' });
      return;
    }

    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:3001/api/ingest_bulk_emails', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ raw_text: bulkEmailsText }),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || `HTTP error! status: ${response.status}`);
      }

      const successMsg = result.message || `Successfully ingested emails.`;
      const count = result.count || 0;
      setFeedback({ 
          type: 'success', 
          message: `${successMsg} Weaviate is now processing ${count > 0 ? count : ''} email(s).` 
      });
      setBulkEmailsText('');

    } catch (error) {
      console.error('Ingestion error:', error);
      setFeedback({ type: 'error', message: `Failed to ingest emails: ${error instanceof Error ? error.message : String(error)}` });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto bg-white rounded-lg shadow-md mt-4 border border-gray-200">
      <h2 className="text-2xl font-semibold mb-5 text-gray-800 border-b pb-2">Ingest Bulk Emails</h2>
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label htmlFor="bulkEmails" className="block text-sm font-medium text-gray-700 mb-1">
            Paste Raw Email Text
          </label>
          <textarea
            id="bulkEmails"
            value={bulkEmailsText}
            onChange={(e) => setBulkEmailsText(e.target.value)}
            rows={20}
            placeholder="Paste one or more emails here, including headers (From, Subject, Date...). Separate emails clearly (e.g., with 'Email 1', 'Email 2' markers or distinct separators)..."
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition duration-150 ease-in-out font-mono text-sm"
            disabled={isLoading}
            required
          />
          <p className="mt-2 text-xs text-gray-500">
            Ensure emails are clearly separated (e.g., starting each with 'Email [number]' on a new line) and include 'From:', 'Subject:', and 'Date:' headers for proper parsing.
          </p>
        </div>
        <div className="flex flex-col sm:flex-row justify-between items-center space-y-3 sm:space-y-0 sm:space-x-4 pt-3 border-t mt-5">
           <div className="flex-grow text-center sm:text-left">
             {feedback && (
               <p className={`text-sm font-medium ${feedback.type === 'success' ? 'text-green-600' : 'text-red-500'}`}>
                 {feedback.message}
               </p>
             )}
          </div>
          <button
            type="submit"
            className={`w-full sm:w-auto px-5 py-2.5 rounded-md text-white font-semibold transition-colors duration-150 ease-in-out flex items-center justify-center ${
              isLoading
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500'
            }`}
            disabled={isLoading}
          >
            {isLoading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Ingesting...
                </>
              ) : (
                'Ingest Emails'
              )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default EmailIngestionForm; 