import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { format } from 'date-fns';
import { FileText, AlertTriangle, DollarSign } from 'lucide-react';

export default function History() {
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const token = localStorage.getItem('token');
        const res = await axios.get('http://localhost:8000/api/history', {
          headers: { Authorization: `Bearer ${token}` }
        });
        setHistory(res.data);
      } catch (err: any) {
        if (err.response?.status === 401) {
          navigate('/login');
        }
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, [navigate]);

  const viewReport = (item: any) => {
    navigate('/report', { state: { report: item } });
  };

  if (loading) return <div className="text-center mt-20 text-gray-400">Loading history...</div>;

  return (
    <div className="py-8">
      <h1 className="text-3xl font-bold mb-6">Analysis History</h1>

      {history.length === 0 ? (
        <div className="bg-gray-800 p-8 rounded-xl border border-gray-700 text-center text-gray-400">
          <p>No analyses found. Head to the dashboard to run your first analysis.</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {history.map((item) => (
            <div
              key={item.id}
              onClick={() => viewReport(item)}
              className="bg-gray-800 border border-gray-700 rounded-xl p-5 hover:border-blue-500 cursor-pointer transition-colors flex justify-between items-center"
            >
              <div>
                <h3 className="text-lg font-bold text-white mb-1">{item.resource_group}</h3>
                <p className="text-sm text-gray-400">
                  {format(new Date(item.created_at), 'MMM dd, yyyy • hh:mm a')}
                </p>
              </div>

              <div className="flex space-x-6">
                <div className="flex items-center space-x-2">
                  <FileText className="text-blue-400" size={18} />
                  <span className="text-sm text-gray-300">{item.resources_scanned} scanned</span>
                </div>
                <div className="flex items-center space-x-2">
                  <AlertTriangle className={item.issues_found > 0 ? "text-yellow-400" : "text-gray-500"} size={18} />
                  <span className="text-sm text-gray-300">{item.issues_found} issues</span>
                </div>
                <div className="flex items-center space-x-2">
                  <DollarSign className="text-green-400" size={18} />
                  <span className="text-sm font-medium text-white">{item.estimated_savings}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
