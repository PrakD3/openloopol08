'use client';

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Shield, Zap, Eye, Globe, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { DEMO_VIDEOS, MOCK_INCIDENTS } from '@/lib/demoData';
import { useMode } from '@/hooks/useMode';
import { useRouter } from 'next/navigation';

export default function HomePage() {
  const { t } = useTranslation();
  const { isDemo } = useMode();
  const router = useRouter();
  const [videoUrl, setVideoUrl] = useState('');
  const [selectedDemo, setSelectedDemo] = useState(DEMO_VIDEOS[0].url);

  const handleAnalyse = () => {
    const url = isDemo ? selectedDemo : videoUrl;
    if (!url) return;
    router.push(`/analysis?url=${encodeURIComponent(url)}&demo=${isDemo}`);
  };

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-b from-background to-secondary/20 py-20 px-4">
        <div className="mx-auto max-w-4xl text-center space-y-6">
          <div className="flex justify-center">
            <Badge variant="secondary" className="text-sm px-4 py-1">
              🛡️ AI-Powered Verification
            </Badge>
          </div>
          <h1 className="text-4xl md:text-6xl font-black tracking-tight">
            {t('home.hero')}
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            {t('home.subtitle')}
          </p>

          {/* Premium Platform Search Bar */}
          <div className="max-w-3xl mx-auto mt-12 relative group">
            <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 rounded-2xl blur opacity-25 group-hover:opacity-50 transition duration-1000 group-hover:duration-200"></div>
            
            <div className="relative bg-black/40 backdrop-blur-2xl border border-white/10 rounded-2xl p-2 shadow-2xl flex flex-col md:flex-row gap-2">
              <div className="flex-1 flex items-center px-4 gap-3">
                <Globe className="text-white/30 h-5 w-5" />
                <input
                  type="url"
                  placeholder="Paste link from YouTube, 𝕏, Instagram, or Reddit..."
                  value={videoUrl}
                  onChange={(e) => setVideoUrl(e.target.value)}
                  className="w-full bg-transparent border-none text-white focus:ring-0 placeholder:text-white/20 text-sm py-3"
                />
              </div>
              
              <button 
                onClick={handleAnalyse}
                className="bg-white text-black hover:bg-white/90 font-bold px-8 py-3 rounded-xl transition-all flex items-center justify-center gap-2 group/btn"
              >
                Analyse Now
                <ArrowRight className="h-4 w-4 group-hover/btn:translate-x-1 transition-transform" />
              </button>
            </div>

            {/* Platform Badges */}
            <div className="flex justify-center gap-6 mt-6 opacity-40 hover:opacity-100 transition-opacity">
              <span className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest">
                <Youtube size={12} className="text-red-500" /> YouTube
              </span>
              <span className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest">
                <Twitter size={12} className="text-blue-400" /> 𝕏 (Twitter)
              </span>
              <span className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest">
                <Instagram size={12} className="text-pink-500" /> Instagram
              </span>
              <span className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest">
                <Globe size={12} className="text-orange-500" /> Reddit
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-16 px-4">
        <div className="mx-auto max-w-6xl">
          <div className="grid md:grid-cols-3 gap-6">
            {[
              { icon: Zap, title: 'DeepFake Detector', desc: 'CrossEfficientViT model analyses every keyframe for AI generation artifacts' },
              { icon: Eye, title: 'Source Hunter', desc: 'Reverse image search + EXIF metadata to find the earliest known source' },
              { icon: Globe, title: 'Context Analyser', desc: 'Whisper transcription + vision LLM verifies location, language, and timing' },
            ].map((feature) => (
              <Card key={feature.title} className="hover:shadow-md transition-shadow">
                <CardHeader>
                  <feature.icon className="h-8 w-8 text-accent mb-2" />
                  <CardTitle className="text-lg">{feature.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">{feature.desc}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Active Incidents Preview */}
      <section className="py-16 px-4 bg-secondary/20">
        <div className="mx-auto max-w-6xl">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold">Active Incidents</h2>
            <Button variant="outline" size="sm" asChild>
              <a href="/incidents">View All <ArrowRight className="ml-1 h-3 w-3" /></a>
            </Button>
          </div>
          <div className="grid md:grid-cols-3 gap-4">
            {MOCK_INCIDENTS.map((incident) => (
              <Card key={incident.id} className="hover:shadow-md transition-shadow">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <Badge variant={incident.verdict as 'real' | 'misleading' | 'unverified'}>
                      {incident.verdict.toUpperCase()}
                    </Badge>
                    <span className="text-xs text-muted-foreground">{incident.date}</span>
                  </div>
                  <CardTitle className="text-sm leading-tight mt-2">{incident.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-muted-foreground">{incident.location}</p>
                  <div className="mt-2 flex items-center gap-2">
                    <div className="flex-1 h-1.5 bg-secondary rounded-full overflow-hidden">
                      <div
                        className="h-full bg-destructive rounded-full"
                        style={{ width: `${incident.misinfoRate}%` }}
                      />
                    </div>
                    <span className="text-xs text-muted-foreground">{incident.misinfoRate}% misinfo</span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="py-16 px-4">
        <div className="mx-auto max-w-4xl">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
            {[
              { value: '2,847', label: 'Videos Analysed' },
              { value: '61%', label: 'Misinformation Rate' },
              { value: '94%', label: 'Detection Accuracy' },
              { value: '< 30s', label: 'Analysis Time' },
            ].map((stat) => (
              <div key={stat.label} className="space-y-1">
                <p className="text-3xl font-black text-accent">{stat.value}</p>
                <p className="text-sm text-muted-foreground">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
