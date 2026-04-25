'use client';

import React, { useEffect, useState } from 'react';
import { AlertCircle, CheckCircle, Info, X } from 'lucide-react';

interface Verdict {
  video_id: string;
  url: string;
  verdict: 'real' | 'misleading' | 'ai-generated' | 'unverified';
  score: number;
  summary: string;
  timestamp: string;
}

const LiveAlerts: React.FC = () => {
  const [alerts, setAlerts] = useState<Verdict[]>([]);

  useEffect(() => {
    // Connect to SSE
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    const eventSource = new EventSource(`${backendUrl}/live-feed`);

    eventSource.onmessage = (event) => {
      const data: Verdict = JSON.parse(event.data);
      setAlerts((prev) => [data, ...prev].slice(0, 3)); // Keep only latest 3
    };

    eventSource.onerror = (err) => {
      console.error('SSE connection error:', err);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, []);

  const removeAlert = (id: string) => {
    setAlerts((prev) => prev.filter((a) => a.video_id !== id));
  };

  if (alerts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-3 w-full max-w-md">
      {alerts.map((alert) => (
        <div
          key={alert.video_id}
          className={`relative p-4 rounded-xl border shadow-2xl backdrop-blur-md animate-in slide-in-from-right transition-all duration-300 ${
            alert.verdict === 'real'
              ? 'bg-red-500/10 border-red-500/50 text-red-100'
              : 'bg-yellow-500/10 border-yellow-500/50 text-yellow-100'
          }`}
        >
          <button
            onClick={() => removeAlert(alert.video_id)}
            className="absolute top-2 right-2 p-1 hover:bg-white/10 rounded-full transition-colors"
          >
            <X size={16} />
          </button>

          <div className="flex gap-3">
            <div className="mt-1">
              {alert.verdict === 'real' ? (
                <AlertCircle className="text-red-400" />
              ) : (
                <Info className="text-yellow-400" />
              )}
            </div>
            <div>
              <h3 className="font-bold text-sm uppercase tracking-wider mb-1">
                {alert.verdict === 'real' ? '🚨 Real Crisis Detected' : '⚠️ Misinformation Flagged'}
              </h3>
              <p className="text-xs opacity-90 leading-relaxed mb-2">
                {alert.summary}
              </p>
              <div className="flex items-center justify-between text-[10px] font-mono opacity-60">
                <span>Confidence: {alert.score}%</span>
                <a
                  href={alert.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline hover:text-white"
                >
                  View Source
                </a>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default LiveAlerts;
