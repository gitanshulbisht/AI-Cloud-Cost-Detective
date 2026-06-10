import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Play } from 'lucide-react';
import ProgressTracker from '../components/ProgressTracker';

export default function Dashboard() {
  const [resourceGroups, setResourceGroups] = useState<string[]>([]);
  const [selectedRg, setSelectedRg] = useState('');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<string[]>([]);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const fetchResourceGroups = async () => {
      try {
        const token = localStorage.getItem('token');
        const res = await axios.get('http://localhost:8000/api/resource-groups', {
          headers: { Authorization: `Bearer ${token}` }
        });
        setResourceGroups(res.data);
        if (res.data.length > 0) setSelectedRg(res.data[0]);
      } catch (err: any) {
        if (err.response?.status === 401) {
          localStorage.removeItem('token');
          navigate('/login');
        }
        setError('Failed to fetch resource groups.');
      }
    };
    fetchResourceGroups();
  }, [navigate]);

  const startAnalysis = async () => {
    if (!selectedRg) return;
    setLoading(true);
    setMessages([]);
    setError('');

    try {
      const token = localStorage.getItem('token');
      const res = await axios.post(
        'http://localhost:8000/api/analyze',
        { resource_group: selectedRg },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      const analysisId = res.data.analysis_id;

      const ws = new WebSocket(`ws://localhost:8000/ws/progress/${analysisId}`);

      ws.onmessage = (event) => {
        const msg = event.data;
        setMessages((prev) => [...prev, msg]);

        if (msg === 'Analysis complete') {
          ws.close();
          setTimeout(() => navigate('/history'), 1500); // Redirect to history/reports after complete
        } else if (msg.startsWith('Error:')) {
            ws.close();
            setLoading(false);
            setError(msg);
        }
      };

      ws.onerror = () => {
        setError('WebSocket connection error.');
        setLoading(false);
      };

    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start analysis');
      setLoading(false);
    }
  };

  return (
    <div className="py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Cost Analysis Dashboard</h1>
        <p className="text-gray-400">Select an Azure Resource Group to start finding cost savings.</p>
      </div>

      <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 max-w-2xl mx-auto shadow-lg">
        {error && <div className="bg-red-500/10 border border-red-500 text-red-500 p-3 rounded mb-4">{error}</div>}

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">Target Resource Group</label>
            <select
              value={selectedRg}
              onChange={(e) => setSelectedRg(e.target.value)}
              disabled={loading || resourceGroups.length === 0}
              className="w-full bg-gray-700 border border-gray-600 rounded-lg p-3 text-white focus:outline-none focus:border-blue-500 disabled:opacity-50"
            >
              {resourceGroups.length === 0 ? (
                <option>Loading...</option>
              ) : (
                resourceGroups.map(rg => (
                  <option key={rg} value={rg}>{rg}</option>
                ))
              )}
            </select>
          </div>

          <button
            onClick={startAnalysis}
            disabled={loading || !selectedRg}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 text-white font-bold py-3 px-4 rounded-lg flex items-center justify-center space-x-2 transition-colors"
          >
            {loading ? (
              <span>Analyzing...</span>
            ) : (
              <>
                <Play size={18} />
                <span>Run Analysis</span>
              </>
            )}
          </button>
        </div>
      </div>

      <ProgressTracker messages={messages} />
    </div>
  );
}
