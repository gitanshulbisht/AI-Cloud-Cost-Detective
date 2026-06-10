import { useLocation, useNavigate } from 'react-router-dom';
import { ShieldAlert, Info, Terminal, ChevronLeft } from 'lucide-react';

export default function Report() {
  const location = useLocation();
  const navigate = useNavigate();
  const reportData = location.state?.report;

  if (!reportData) {
    return (
      <div className="text-center mt-20 text-gray-400">
        <p>No report data found.</p>
        <button onClick={() => navigate('/history')} className="text-blue-400 mt-4 hover:underline">Go to History</button>
      </div>
    );
  }

  const { analysis_result } = reportData;

  const severityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'high': return 'bg-red-500/20 text-red-400 border-red-500/50';
      case 'medium': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50';
      case 'low': return 'bg-green-500/20 text-green-400 border-green-500/50';
      default: return 'bg-gray-500/20 text-gray-400 border-gray-500/50';
    }
  };

  return (
    <div className="py-8">
      <button
        onClick={() => navigate(-1)}
        className="flex items-center space-x-1 text-gray-400 hover:text-white mb-6 transition-colors"
      >
        <ChevronLeft size={20} />
        <span>Back</span>
      </button>

      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold mb-2">Cost Analysis Report</h1>
          <p className="text-gray-400">Resource Group: <span className="text-white font-medium">{reportData.resource_group}</span></p>
        </div>
        <div className="text-right">
          <div className="text-sm text-gray-400 mb-1">Estimated Monthly Savings</div>
          <div className="text-3xl font-bold text-green-400">{reportData.estimated_savings}</div>
        </div>
      </div>

      <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 mb-8 shadow-lg">
        <h2 className="text-xl font-bold mb-3 flex items-center space-x-2">
          <Info className="text-blue-400" />
          <span>AI Summary</span>
        </h2>
        <p className="text-gray-300 leading-relaxed">
          {analysis_result?.summary || "No summary provided."}
        </p>
        <div className="mt-4 flex space-x-4 border-t border-gray-700 pt-4">
          <div className="text-sm text-gray-400">Resources Scanned: <span className="text-white font-bold">{reportData.resources_scanned}</span></div>
          <div className="text-sm text-gray-400">Issues Found: <span className="text-white font-bold">{reportData.issues_found}</span></div>
        </div>
      </div>

      <h2 className="text-2xl font-bold mb-4">Detected Issues ({reportData.issues_found})</h2>

      {analysis_result?.issues && analysis_result.issues.length > 0 ? (
        <div className="space-y-6">
          {analysis_result.issues.map((issue: any, idx: number) => (
            <div key={idx} className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden shadow-md">
              <div className="p-5 border-b border-gray-700 flex justify-between items-start">
                <div>
                  <h3 className="text-lg font-bold text-white mb-1 flex items-center space-x-2">
                    <ShieldAlert size={18} className="text-yellow-500" />
                    <span>{issue.resource_name}</span>
                  </h3>
                  <p className="text-sm text-gray-400 capitalize">{issue.issue_type}</p>
                </div>
                <span className={`px-3 py-1 rounded-full text-xs font-bold border ${severityColor(issue.severity)}`}>
                  {issue.severity.toUpperCase()}
                </span>
              </div>

              <div className="p-5">
                <p className="text-gray-300 mb-4">{issue.explanation}</p>

                {issue.fix_command && (
                  <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
                    <div className="flex items-center space-x-2 mb-2 text-sm text-gray-400 font-mono">
                      <Terminal size={14} />
                      <span>Suggested Fix</span>
                    </div>
                    <code className="text-green-400 text-sm break-all font-mono">
                      {issue.fix_command}
                    </code>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-gray-800 p-8 rounded-xl border border-gray-700 text-center">
          <p className="text-green-400 font-medium">Great news! No cost-saving issues were found.</p>
        </div>
      )}
    </div>
  );
}
