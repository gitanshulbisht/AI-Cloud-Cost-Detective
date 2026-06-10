import { CheckCircle2, Loader2 } from 'lucide-react';

interface ProgressTrackerProps {
  messages: string[];
}

export default function ProgressTracker({ messages }: ProgressTrackerProps) {
  if (messages.length === 0) return null;

  return (
    <div className="mt-8 bg-gray-800 p-6 rounded-xl border border-gray-700 max-w-2xl mx-auto">
      <h3 className="text-lg font-semibold mb-4">Analysis Progress</h3>
      <div className="space-y-4">
        {messages.map((msg, idx) => {
          const isLast = idx === messages.length - 1;
          const isComplete = msg === "Analysis complete" || !isLast;

          return (
            <div key={idx} className="flex items-center space-x-3">
              {isComplete ? (
                <CheckCircle2 className="text-green-500 w-5 h-5" />
              ) : (
                <Loader2 className="text-blue-500 w-5 h-5 animate-spin" />
              )}
              <span className={isComplete ? "text-gray-300" : "text-white font-medium"}>
                {msg}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
