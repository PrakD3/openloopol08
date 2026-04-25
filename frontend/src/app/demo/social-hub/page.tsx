'use client';

import React, { useState } from 'react';
import { Instagram, Twitter, Youtube, Music2, Search, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import LiveAlerts from '@/components/notifications/LiveAlerts';

const platforms = [
  { id: 'instagram', icon: Instagram, color: 'from-purple-600 to-pink-500', name: 'Instagram Reels' },
  { id: 'twitter', icon: Twitter, color: 'from-blue-400 to-blue-600', name: '𝕏 (Twitter)' },
  { id: 'youtube', icon: Youtube, color: 'from-red-600 to-red-700', name: 'YouTube Shorts' },
  { id: 'tiktok', icon: Music2, color: 'from-black to-slate-800', name: 'TikTok' },
];

const SocialHub = () => {
  const [activeTab, setActiveTab] = useState('instagram');

  return (
    <div className="min-h-screen bg-[#050505] text-white font-sans selection:bg-blue-500/30">
      {/* Background Decor */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-600/10 blur-[120px] rounded-full" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-600/10 blur-[120px] rounded-full" />
      </div>

      <LiveAlerts />

      <header className="relative z-10 border-b border-white/5 bg-black/40 backdrop-blur-xl sticky top-0">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="p-2 hover:bg-white/5 rounded-full transition-colors">
              <ArrowLeft size={20} />
            </Link>
            <div>
              <h1 className="text-xl font-bold tracking-tight">Social Integration Hub</h1>
              <p className="text-[10px] text-white/40 uppercase tracking-[0.2em]">Real-Time Overlay Simulation</p>
            </div>
          </div>
          
          <div className="flex items-center gap-6">
             <div className="hidden md:flex gap-1 bg-white/5 p-1 rounded-full border border-white/10">
                {platforms.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => setActiveTab(p.id)}
                    className={`px-4 py-2 rounded-full text-xs font-medium transition-all flex items-center gap-2 ${
                      activeTab === p.id ? 'bg-white text-black shadow-lg' : 'hover:bg-white/5 text-white/60'
                    }`}
                  >
                    <p.icon size={14} />
                    {p.name}
                  </button>
                ))}
             </div>
          </div>
        </div>
      </header>

      <main className="relative z-10 max-w-7xl mx-auto px-6 py-12">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* Left: Device Mockup */}
          <div className="lg:col-span-4 flex justify-center">
            <div className="relative w-[320px] h-[640px] bg-black rounded-[3rem] border-[8px] border-[#1a1a1a] shadow-[0_0_0_2px_rgba(255,255,255,0.05),0_30px_60px_-12px_rgba(0,0,0,0.5)] overflow-hidden">
              {/* Dynamic Content based on activeTab */}
              <div className={`absolute inset-0 bg-gradient-to-b ${platforms.find(p => p.id === activeTab)?.color} opacity-20`} />
              
              <div className="absolute inset-0 flex flex-col p-6">
                <div className="flex justify-between items-center mb-8">
                  <div className="w-12 h-2 bg-white/20 rounded-full" />
                  <div className="flex gap-2">
                    <div className="w-4 h-4 bg-white/20 rounded-full" />
                    <div className="w-4 h-4 bg-white/20 rounded-full" />
                  </div>
                </div>

                <div className="flex-1 flex flex-col justify-center items-center text-center">
                  <div className="w-20 h-20 rounded-3xl bg-white/10 backdrop-blur-xl border border-white/10 flex items-center justify-center mb-6 animate-pulse">
                    {React.createElement(platforms.find(p => p.id === activeTab)?.icon || Instagram, { size: 40 })}
                  </div>
                  <h2 className="text-lg font-bold mb-2">Simulated {activeTab} Feed</h2>
                  <p className="text-xs text-white/50 px-8 leading-relaxed">
                    Scroll through your {activeTab} feed as usual. Vigilens Watcher will automatically flag content in real-time.
                  </p>
                </div>

                {/* Simulated Post Card */}
                <div className="mt-auto bg-white/5 border border-white/10 rounded-2xl p-4 backdrop-blur-md mb-8">
                  <div className="flex gap-3 mb-3">
                    <div className="w-8 h-8 rounded-full bg-white/10" />
                    <div className="flex-1">
                      <div className="w-20 h-2 bg-white/20 rounded-full mb-1.5" />
                      <div className="w-12 h-1.5 bg-white/10 rounded-full" />
                    </div>
                  </div>
                  <div className="aspect-[4/5] bg-white/5 rounded-lg border border-white/5 mb-3 flex items-center justify-center italic text-[10px] text-white/20">
                    Video Content Rendering...
                  </div>
                  <div className="flex gap-4">
                    <div className="w-4 h-4 bg-white/20 rounded-full" />
                    <div className="w-4 h-4 bg-white/20 rounded-full" />
                    <div className="w-4 h-4 bg-white/20 rounded-full" />
                  </div>
                </div>
              </div>
              
              {/* Notch */}
              <div className="absolute top-0 left-1/2 -translate-x-1/2 w-32 h-6 bg-black rounded-b-2xl" />
            </div>
          </div>

          {/* Right: Monitoring Console */}
          <div className="lg:col-span-8">
            <div className="bg-white/[0.02] border border-white/5 rounded-[2rem] p-8 backdrop-blur-xl h-full flex flex-col">
              <div className="flex items-center justify-between mb-8">
                <div>
                  <h3 className="text-2xl font-bold tracking-tight mb-1">Backend Monitoring Console</h3>
                  <p className="text-sm text-white/40">Watch as Vigilens polls social media APIs every 60 seconds.</p>
                </div>
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-green-500/10 border border-green-500/20 text-green-400 text-[10px] font-bold uppercase tracking-widest">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                  Active Listener
                </div>
              </div>

              <div className="flex-1 space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="group p-5 rounded-2xl bg-white/[0.03] border border-white/5 hover:border-white/10 transition-all cursor-default">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center text-xs">
                          {i === 1 ? '📹' : i === 2 ? '𝕏' : '📸'}
                        </div>
                        <div className="text-xs font-medium text-white/80">
                          {i === 1 ? 'YouTube Polling...' : i === 2 ? 'X Search Update' : 'IG Reel Scraped'}
                        </div>
                      </div>
                      <div className="text-[10px] font-mono text-white/30">Just now</div>
                    </div>
                    <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                      <div className="h-full bg-blue-500 rounded-full w-[40%] group-hover:w-full transition-all duration-[3000ms]" />
                    </div>
                  </div>
                ))}

                <div className="p-8 rounded-3xl border border-dashed border-white/10 flex flex-col items-center justify-center text-center opacity-40">
                  <Search size={32} className="mb-4 text-white/20" />
                  <p className="text-xs">Waiting for new {activeTab} uploads...</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default SocialHub;
