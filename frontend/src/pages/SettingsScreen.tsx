import React, { useState, useEffect, useCallback } from 'react';
import { useOutletContext } from 'react-router-dom';

// Interface for settings data matching the backend Pydantic model
interface UserSettings {
    urgent_context: string;
    delegate_context: string;
    loop_context: string;
}

// Interface for chat history message (match MainLayout)
interface Message {
    id: string;
    sender: 'user' | 'assistant';
    text: string;
    references?: any[]; // Keep flexible
}

// Context type provided by Outlet
interface OutletContextType {
  chatHistory: Message[];
}

const SettingsScreen: React.FC = () => {
    // Access chatHistory from the Outlet context
    const { chatHistory } = useOutletContext<OutletContextType>();

    const [urgentContext, setUrgentContext] = useState('');
    const [delegateContext, setDelegateContext] = useState('');
    const [loopContext, setLoopContext] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [isInitiallyLoading, setIsInitiallyLoading] = useState(true);
    const [feedback, setFeedback] = useState<{ type: 'success' | 'error' | 'info'; message: string } | null>(null);

    // --- Load Settings --- 
    const loadSettings = useCallback(async () => {
        setIsInitiallyLoading(true);
        setFeedback(null);
        try {
            const response = await fetch('http://localhost:3001/api/settings');
            if (!response.ok) {
                 const errorData = await response.json().catch(() => ({ detail: "Unknown error" }));
                 throw new Error(errorData.detail || `HTTP error ${response.status}`);
            }
            const data: UserSettings = await response.json();
            setUrgentContext(data.urgent_context || '');
            setDelegateContext(data.delegate_context || '');
            setLoopContext(data.loop_context || '');
        } catch (error) {
            console.error("Load settings error:", error);
            setFeedback({ type: 'error', message: `Failed to load settings: ${error instanceof Error ? error.message : String(error)}` });
        } finally {
            setIsInitiallyLoading(false);
        }
    }, []);

    useEffect(() => {
        loadSettings();
    }, [loadSettings]);
    // --- End Load Settings ---

    // --- Save Settings --- 
    const handleSave = async () => {
        setIsLoading(true);
        setFeedback(null);
        const currentSettings: UserSettings = { 
            urgent_context: urgentContext, 
            delegate_context: delegateContext, 
            loop_context: loopContext 
        };
        console.log("Saving settings:", currentSettings);
        
        try {
            const response = await fetch('http://localhost:3001/api/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(currentSettings),
            });
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.detail || `HTTP error ${response.status}`);
            }
            setFeedback({ type: 'success', message: result.message || 'Settings saved successfully!' });
        } catch (error) {
             console.error("Save settings error:", error);
             setFeedback({ type: 'error', message: `Failed to save settings: ${error instanceof Error ? error.message : String(error)}` });
        } finally {
             setIsLoading(false);
        }
    };
    // --- End Save Settings --- 

    const handleReset = (setter: React.Dispatch<React.SetStateAction<string>>) => {
         // TODO: Reset to default values if applicable (Phase 2/4) -> For now, just clears local state
        setter('');
        setFeedback(null); // Clear feedback on reset
    };

    // --- Updated Learn Handler --- 
    const handleLearn = async () => { // Make async
        setIsLoading(true); // Reuse isLoading state
        setFeedback({ type: 'info', message: 'Analyzing chat history...' });
        
        // Filter user questions from the current session's history
        const userQuestions = chatHistory
            .filter(msg => msg.sender === 'user')
            .map(msg => msg.text);
            
        if (userQuestions.length === 0) {
             setFeedback({ type: 'info', message: 'No user questions found in current session history to learn from.' });
             setIsLoading(false);
             return;
        }
        
        console.log(`Sending ${userQuestions.length} questions to summarize.`);

        try {
            const response = await fetch('http://localhost:3001/api/summarize_questions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ questions: userQuestions }),
            });
            const result = await response.json();
            if (!response.ok) {
                 throw new Error(result.detail || `HTTP error ${response.status}`);
            }
            
            const summary = result.summary;
            if (summary) {
                 // Append summary to the existing urgent context
                 setUrgentContext(prev => (prev ? prev + '\n\n' : '') + `Learned from chat: ${summary}`);
                 setFeedback({ type: 'success', message: 'Identified potential important topics from chat history and added to Urgent/Important context.' });
            } else {
                 setFeedback({ type: 'info', message: 'Could not generate a summary from chat history.' });
            }

        } catch (error) {
             console.error("Learn from chat error:", error);
             setFeedback({ type: 'error', message: `Failed to learn from chat: ${error instanceof Error ? error.message : String(error)}` });
        } finally {
            setIsLoading(false);
        }
    };
    // --- End Learn Handler ---

    // --- Render Logic --- 
    if (isInitiallyLoading) {
         return <div className="flex justify-center items-center h-64">Loading Settings...</div>;
    }

    return (
        <div className="p-6 max-w-4xl mx-auto space-y-8">
            <h1 className="text-3xl font-semibold text-gray-800 border-b pb-3">Settings</h1>

            {/* --- What is Urgent/Important --- */}
            <section className="space-y-3 p-4 border rounded-lg shadow-sm">
                <h2 className="text-xl font-medium text-gray-700">Define Urgent/Important Emails</h2>
                <p className="text-sm text-gray-500">
                    Describe what makes an email urgent or important for you (e.g., keywords like 'deadline', specific projects, senders like CEO).
                    This context helps prioritize emails on the homescreen and in summaries.
                </p>
                <textarea
                    rows={4}
                    value={urgentContext}
                    onChange={(e) => setUrgentContext(e.target.value)}
                    placeholder="e.g., Emails from Michael Farlekas, subject contains 'Board Meeting', mentions 'Project Redwood deadline'..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition duration-150 ease-in-out"
                />
                <div className="flex justify-end items-center space-x-3">
                     <button 
                         onClick={handleLearn} 
                         className="text-sm text-indigo-600 hover:text-indigo-800 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
                         title="Summarize recent chat questions to identify important topics"
                         disabled={isLoading} // Disable while loading
                     >
                         Learn from Chat History
                    </button>
                     <button onClick={() => handleReset(setUrgentContext)} className="text-sm text-gray-500 hover:text-gray-700 focus:outline-none">
                        Reset
                    </button>
                </div>
            </section>

            {/* --- Delegation --- */}
            <section className="space-y-3 p-4 border rounded-lg shadow-sm">
                <h2 className="text-xl font-medium text-gray-700">Define Delegatable Emails</h2>
                <p className="text-sm text-gray-500">
                    Describe emails that can typically be delegated and to whom (e.g., IT issues to support, marketing questions to Garrett).
                </p>
                <textarea
                    rows={4}
                    value={delegateContext}
                    onChange={(e) => setDelegateContext(e.target.value)}
                    placeholder="e.g., General marketing inquiries to Garrett Denney, Technical support requests to IT Support, Scheduling requests to Admin Assistant..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition duration-150 ease-in-out"
                />
                 <div className="flex justify-end">
                     <button onClick={() => handleReset(setDelegateContext)} className="text-sm text-gray-500 hover:text-gray-700 focus:outline-none">
                        Reset
                    </button>
                </div>
            </section>

            {/* --- Keep in Loop --- */}
            <section className="space-y-3 p-4 border rounded-lg shadow-sm">
                <h2 className="text-xl font-medium text-gray-700">Define 'Keep in Loop' Emails</h2>
                <p className="text-sm text-gray-500">
                    Describe topics or threads you want to be aware of but don't require immediate action (e.g., updates on specific projects, team announcements).
                </p>
                <textarea
                    rows={4}
                    value={loopContext}
                    onChange={(e) => setLoopContext(e.target.value)}
                    placeholder="e.g., Weekly project status reports, HR announcements, Industry news summaries..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition duration-150 ease-in-out"
                />
                 <div className="flex justify-end">
                     <button onClick={() => handleReset(setLoopContext)} className="text-sm text-gray-500 hover:text-gray-700 focus:outline-none">
                        Reset
                    </button>
                </div>
            </section>

             {/* --- Save Button & Feedback --- */}
            <div className="flex justify-end items-center space-x-4 pt-4 border-t">
                {feedback && (
                    <p className={`text-sm font-medium ${feedback.type === 'success' ? 'text-green-600' : feedback.type === 'error' ? 'text-red-500' : 'text-blue-600'}`}>
                        {feedback.message}
                    </p>
                )}
                <button
                    onClick={handleSave}
                    className={`px-5 py-2.5 rounded-md text-white font-semibold transition-colors duration-150 ease-in-out flex items-center justify-center ${
                        isLoading
                            ? 'bg-gray-400 cursor-not-allowed'
                            : 'bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500'
                        }`}
                    disabled={isLoading}
                >
                    {isLoading ? 'Saving...' : 'Save Settings'}
                </button>
            </div>

        </div>
    );
};

export default SettingsScreen; 