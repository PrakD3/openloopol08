'use client';

import React, { useEffect, useState } from 'react';
import { AlertCircle, CheckCircle, Info, X } from 'lucide-react';

interface Verdict {
  video_id: string;
  url: string;
  platform: 'youtube' | 'instagram' | 'twitter' | 'tiktok' | 'facebook' | 'web';
  verdict: 'real' | 'misleading' | 'ai-generated' | 'unverified';
  score: number;
  summary: string;
  timestamp: string;
}

const LiveAlerts: React.FC = () => {
  const [alerts, setAlerts] = useState<Verdict[]>([]);

  const getPlatformIcon = (platform: string) => {
    switch (platform) {
      case 'youtube': return '📹';
      case 'instagram': return '📸';
      case 'twitter': return '𝕏';
      case 'tiktok': return '🎵';
      default: return '🌐';
    }
  };

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
    <div className="fixed bottom-6 left-6 z-[9999] flex flex-col gap-3 w-full max-w-sm">
      {alerts.map((alert) => (
        <div
          key={alert.video_id}
          className={`relative p-4 rounded-2xl border shadow-2xl backdrop-blur-xl animate-in slide-in-from-left transition-all duration-500 ${
            alert.verdict === 'real'
              ? 'bg-red-950/40 border-red-500/50 text-red-100 ring-1 ring-red-500/20'
              : 'bg-yellow-950/40 border-yellow-500/50 text-yellow-100 ring-1 ring-yellow-500/20'
          }`}
        >
          <button
            onClick={() => removeAlert(alert.video_id)}
            className="absolute top-2 right-2 p-1 hover:bg-white/10 rounded-full transition-colors"
          >
            <X size={14} />
          </button>

          <div className="flex gap-3">
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-white/10 flex items-center justify-center text-xl shadow-inner">
              {getPlatformIcon(alert.platform)}
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[10px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded bg-white/10 border border-white/10">
                  {alert.platform} Integration
                </span>
              </div>
              <h3 className="font-bold text-sm tracking-tight mb-1">
                {alert.verdict === 'real' ? '🚨 VERIFIED EMERGENCY' : '⚠️ CONTENT WARNING'}
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
