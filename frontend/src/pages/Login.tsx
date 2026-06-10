import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await axios.post('http://localhost:8000/api/auth/login', { email, password });
      localStorage.setItem('token', res.data.access_token);
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed');
    }
  };

  return (
    <div className="max-w-md mx-auto mt-20 bg-gray-800 p-8 rounded-xl shadow-lg border border-gray-700">
      <h2 className="text-2xl font-bold text-center mb-6">Welcome Back</h2>
      {error && <div className="bg-red-500/10 border border-red-500 text-red-500 p-3 rounded mb-4 text-center">{error}</div>}
      <form onSubmit={handleLogin} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-400 mb-1">Email</label>
          <input
            type="email"
            className="w-full bg-gray-700 border border-gray-600 rounded p-2 focus:outline-none focus:border-blue-500"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-400 mb-1">Password</label>
          <input
            type="password"
            className="w-full bg-gray-700 border border-gray-600 rounded p-2 focus:outline-none focus:border-blue-500"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        <button type="submit" className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded transition-colors">
          Login
        </button>
      </form>
      <div className="mt-4 text-center text-gray-400 text-sm">
        Don't have an account? <Link to="/signup" className="text-blue-400 hover:underline">Sign up</Link>
      </div>
    </div>
  );
}
