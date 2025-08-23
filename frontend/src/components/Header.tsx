import React from 'react';
import { Link } from 'react-router-dom';
import { Shield } from 'lucide-react';

const Header: React.FC = () => {
  return (
    <header className="bg-white shadow-sm border-b">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center py-6">
          <Link to="/" className="flex items-center">
            <Shield className="h-8 w-8 text-indigo-600" />
            <span className="ml-2 text-2xl font-bold text-gray-900">DepScan</span>
          </Link>
          
          <nav className="flex space-x-8">
            <Link
              to="/"
              className="text-gray-500 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
            >
              Home
            </Link>
            <Link
              to="/scan"
              className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-md text-sm font-medium"
            >
              New Scan
            </Link>
          </nav>
        </div>
      </div>
    </header>
  );
};

export default Header;