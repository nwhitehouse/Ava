import React, { lazy, Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';
import './index.css'; // Import Tailwind styles here

// Import Layout
import MainLayout from './components/MainLayout';

// Lazy load pages for better initial load performance
const HomeScreen = lazy(() => import('./pages/HomeScreen'));
const EmailDetailScreen = lazy(() => import('./pages/EmailDetailScreen')); // Import new detail page
const EmailListScreen = lazy(() => import('./pages/EmailListScreen')); // Import new list page
const SettingsScreen = lazy(() => import('./pages/SettingsScreen')); // Import SettingsScreen

const App: React.FC = () => {
  return (
    <Suspense fallback={<div className="flex justify-center items-center h-screen">Loading...</div>}>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          {/* Define nested routes that will render inside MainLayout's <Outlet> */}
          <Route index element={<HomeScreen />} />
          {/* Add route for the email list page */}
          <Route path="emails" element={<EmailListScreen />} />
          {/* Add route for the email detail page with parameter */}
          <Route path="email/:emailId" element={<EmailDetailScreen />} />
          <Route path="settings" element={<SettingsScreen />} /> {/* Add settings route */}
          {/* You could add other routes here later */}
          {/* Example: <Route path="settings" element={<SettingsScreen />} /> */}
        </Route>
        {/* Add non-layout routes here (e.g., Login page) */}
        {/* <Route path="/login" element={<LoginPage />} /> */}
      </Routes>
    </Suspense>
  );
};

export default App;
