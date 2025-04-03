import { Routes, Route } from 'react-router-dom';
import './index.css'; // Import Tailwind styles here

// Import Layout
import MainLayout from './components/MainLayout';

// Import page components
import HomeScreen from './pages/HomeScreen';
import EmailViewScreen from './pages/EmailViewScreen';
import SettingsScreen from './pages/SettingsScreen';

function App() {
  return (
    // Routes are now nested within the MainLayout
    <Routes>
      <Route element={<MainLayout />}>
        {/* Pages rendered inside MainLayout's <Outlet /> */}
        <Route path="/" element={<HomeScreen />} />
        <Route path="/email/:id" element={<EmailViewScreen />} />
        <Route path="/settings" element={<SettingsScreen />} />
        {/* Add other nested routes here */}
      </Route>
      {/* Add non-layout routes here (e.g., Login page) */}
      {/* <Route path="/login" element={<LoginPage />} /> */}
    </Routes>
  );
}

export default App;
