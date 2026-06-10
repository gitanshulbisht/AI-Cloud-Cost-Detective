import { Link, useNavigate } from 'react-router-dom';
import { Cloud, LogOut } from 'lucide-react';

export default function Navbar() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  return (
    <nav className="bg-gray-800 border-b border-gray-700 p-4">
      <div className="container mx-auto max-w-6xl flex justify-between items-center">
        <Link to="/" className="flex items-center space-x-2 text-xl font-bold text-white">
          <Cloud className="text-blue-400" />
          <span>Cost Detective</span>
        </Link>

        {token && (
          <div className="flex items-center space-x-6">
            <Link to="/" className="hover:text-blue-400 transition-colors">Dashboard</Link>
            <Link to="/history" className="hover:text-blue-400 transition-colors">History</Link>
            <button
              onClick={handleLogout}
              className="flex items-center space-x-1 text-red-400 hover:text-red-300 transition-colors"
            >
              <LogOut size={18} />
              <span>Logout</span>
            </button>
          </div>
        )}
      </div>
    </nav>
  );
}
