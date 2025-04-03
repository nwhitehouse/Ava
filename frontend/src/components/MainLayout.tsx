import React from 'react';
import { Link, Outlet } from 'react-router-dom';
import { VscMenu, VscMail, VscArrowUp } from "react-icons/vsc"; // Using VSC icons for now
import { FiChevronLeft } from "react-icons/fi"; // Icon for logo

const MainLayout: React.FC = () => {
  // TODO: Add state for notification visibility
  const showNotification = true; // Example state

  return (
    // Overall container - enforce white background, Jura font is default via Tailwind config
    <div className="flex flex-col h-screen bg-white text-gray-800">
      {/* Top Navigation Bar - removed shadow, adjusted padding */}
      <nav className="bg-white p-4 flex justify-between items-center sticky top-0 z-10 border-b border-gray-200">
        {/* Logo - Using chevron left rotated */}
        <Link to="/" className="text-blue-600 text-3xl transform -rotate-90">
          <FiChevronLeft />
        </Link>
        <div className="flex items-center space-x-4">
          {/* Mail Icon - adjusted color, added notification */}
          <button className="text-gray-600 hover:text-blue-600 relative">
            <VscMail size={24} />
            {showNotification && (
              <span className="absolute top-0 right-0 block h-2 w-2 rounded-full ring-1 ring-white bg-red-500"></span>
            )}
          </button>
          {/* Menu Icon - adjusted color */}
          <button className="text-gray-600 hover:text-blue-600">
            <VscMenu size={24} />
          </button>
        </div>
      </nav>

      {/* Main Content Area - adjusted padding */}
      <main className="flex-grow overflow-y-auto p-6">
        <Outlet /> {/* Child routes will render here */}
      </main>

      {/* Bottom Input Bar - removed shadow, adjusted padding */}
      <footer className="bg-white p-3 sticky bottom-0 z-10 border-t border-gray-200">
        <div className="relative max-w-3xl mx-auto"> { /* Constrain width */ }
          <input
            type="text"
            placeholder="How can I help?"
            // Updated styling: thinner border, less padding, specific colors
            className="w-full py-2 px-4 pr-12 border border-gray-300 rounded-full bg-white text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
          />
          {/* Button styling to match screenshot */}
          <button className="absolute right-1.5 top-1/2 transform -translate-y-1/2 bg-blue-600 hover:bg-blue-700 text-white w-8 h-8 flex items-center justify-center rounded-full">
            <VscArrowUp size={18} />
          </button>
        </div>
      </footer>
    </div>
  );
};

export default MainLayout; 