'use client';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { useMode } from '@/hooks/useMode';
import { DEMO_VIDEOS, MOCK_INCIDENTS } from '@/lib/demoData';
import { cn } from '@/lib/utils';
import { ArrowRight, Eye, Globe, Zap } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

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
    <div className="min-h-screen bg-background selection:bg-accent selection:text-accent-foreground">
      {/* Hero Section */}
      <section className="relative overflow-hidden border-b-6 border-foreground bg-secondary/30 py-24 px-4 bk-noise">
        <div className="mx-auto max-w-4xl text-center space-y-8">
          <div className="flex justify-center animate-bounce-in">
            <Badge
              variant="accent"
              className="text-sm px-6 py-2 border-3 border-foreground bk-shadow-sm"
            >
              🛡️ AI-POWERED VERIFICATION
            </Badge>
          </div>
          <h1 className="text-5xl md:text-8xl font-black uppercase tracking-tighter leading-[0.9] bk-text-shadow">
            {t('home.hero')}
          </h1>
          <p className="text-xl md:text-2xl font-bold max-w-2xl mx-auto border-3 border-foreground p-4 bg-background bk-shadow-sm">
            {t('home.subtitle')}
          </p>

          {/* Video Submission */}
          <div className="max-w-2xl mx-auto mt-12 bg-background border-4 border-foreground p-8 bk-shadow-lg">
            {isDemo ? (
              <div className="space-y-4">
                <p className="text-sm font-black uppercase tracking-widest text-muted-foreground">
                  Select a demo video to analyse:
                </p>
                <div className="grid gap-3">
                  {DEMO_VIDEOS.map((video) => (
                    <button
                      type="button"
                      key={video.id}
                      onClick={() => setSelectedDemo(video.url)}
                      className={cn(
                        'text-left p-4 border-3 transition-all font-bold',
                        selectedDemo === video.url
                          ? 'bg-accent border-foreground translate-x-[4px] translate-y-[4px]'
                          : 'bg-background border-foreground/30 hover:border-foreground hover:bg-muted'
                      )}
                    >
                      {video.label}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="flex gap-4">
                <Input
                  type="url"
                  placeholder={t('home.submitPlaceholder')}
                  value={videoUrl}
                  onChange={(e) => setVideoUrl(e.target.value)}
                  className="flex-1 text-lg h-14"
                />
              </div>
            )}
            <Button
              onClick={handleAnalyse}
              size="xl"
              variant="default"
              className="w-full mt-6 text-xl"
            >
              {t('home.analyseButton')}
              <ArrowRight className="ml-2 h-6 w-6" />
            </Button>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-24 px-4 bg-background">
        <div className="mx-auto max-w-6xl">
          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                icon: Zap,
                title: 'DeepFake Detector',
                desc: 'CrossEfficientViT model analyses every keyframe for AI generation artifacts',
                color: 'bg-clash-3',
              },
              {
                icon: Eye,
                title: 'Source Hunter',
                desc: 'Reverse image search + EXIF metadata to find the earliest known source',
                color: 'bg-secondary',
              },
              {
                icon: Globe,
                title: 'Context Analyser',
                desc: 'Whisper transcription + vision LLM verifies location, language, and timing',
                color: 'bg-clash-2',
              },
            ].map((feature) => (
              <Card key={feature.title} className="bk-hover-scale cursor-pointer group">
                <CardHeader className={cn('border-b-4', feature.color)}>
                  <feature.icon className="h-12 w-12 text-foreground mb-4 group-hover:rotate-12 transition-transform" />
                  <CardTitle className="text-2xl font-black">{feature.title}</CardTitle>
                </CardHeader>
                <CardContent className="bg-background pt-6">
                  <p className="font-bold leading-relaxed">{feature.desc}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Active Incidents Preview */}
      <section className="py-24 px-4 bg-clash-4/20 border-y-6 border-foreground bk-diagonal-lines">
        <div className="mx-auto max-w-6xl">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between mb-12 gap-4">
            <h2 className="text-4xl md:text-6xl font-black uppercase tracking-tighter">
              Active Incidents
            </h2>
            <Button variant="accent" size="lg" asChild className="bk-shadow-md">
              <a href="/incidents">
                View All <ArrowRight className="ml-2 h-5 w-5" />
              </a>
            </Button>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {MOCK_INCIDENTS.map((incident) => (
              <Card key={incident.id} className="bk-hover border-4">
                <CardHeader className="pb-4 bg-muted/30">
                  <div className="flex items-center justify-between mb-4">
                    <Badge
                      variant={incident.verdict as 'real' | 'misleading' | 'unverified'}
                      className="border-2"
                    >
                      {incident.verdict.toUpperCase()}
                    </Badge>
                    <span className="text-xs font-black uppercase tracking-tighter">
                      {incident.date}
                    </span>
                  </div>
                  <CardTitle className="text-lg font-black leading-tight">
                    {incident.title}
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-4">
                  <p className="text-sm font-bold text-muted-foreground uppercase tracking-widest">
                    {incident.location}
                  </p>
                  <div className="mt-6">
                    <div className="flex justify-between items-end mb-2">
                      <span className="text-xs font-black uppercase">Misinfo Rate</span>
                      <span className="text-lg font-black">{incident.misinfoRate}%</span>
                    </div>
                    <div className="h-6 bg-background border-3 border-foreground overflow-hidden bk-shadow-sm">
                      <div
                        className="h-full bg-destructive border-r-3 border-foreground"
                        style={{ width: `${incident.misinfoRate}%` }}
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="py-24 px-4 bg-background">
        <div className="mx-auto max-w-6xl">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            {[
              { value: '2,847', label: 'Videos Analysed', color: 'text-primary' },
              { value: '61%', label: 'Misinformation Rate', color: 'text-clash-1' },
              { value: '94%', label: 'Detection Accuracy', color: 'text-accent' },
              { value: '< 30s', label: 'Analysis Time', color: 'text-secondary' },
            ].map((stat) => (
              <div
                key={stat.label}
                className="p-8 border-4 border-foreground bg-background bk-shadow-md text-center space-y-2"
              >
                <p className={cn('text-5xl font-black', stat.color)}>{stat.value}</p>
                <p className="text-sm font-black uppercase tracking-widest text-muted-foreground">
                  {stat.label}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
