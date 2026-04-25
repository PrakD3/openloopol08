'use client';

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Shield, Zap, Eye, Globe, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useMode } from '@/hooks/useMode';
import { cn } from '@/lib/utils';
import { useRouter } from 'next/navigation';

export default function HomePage() {
  const { t } = useTranslation();
  const { isDemo } = useMode();
  const router = useRouter();
  const [videoUrl, setVideoUrl] = useState('');

  const handleAnalyse = () => {
    if (!videoUrl) return;
    router.push(`/analysis?url=${encodeURIComponent(videoUrl)}`);
  };

  return (
    <div className="min-h-screen bg-background selection:bg-accent selection:text-accent-foreground">
      {/* Hero Section */}
      <section className="relative overflow-hidden border-b-6 border-foreground bg-secondary/30 py-24 px-4 bk-noise">
        <div className="mx-auto max-w-4xl text-center space-y-8">
          <div className="flex justify-center animate-bounce-in">
            <Badge variant="accent" className="text-sm px-6 py-2 border-3 border-foreground bk-shadow-sm">
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
            <div className="flex gap-4">
              <Input
                type="url"
                placeholder={t('home.submitPlaceholder')}
                value={videoUrl}
                onChange={(e) => setVideoUrl(e.target.value)}
                className="flex-1 text-lg h-14"
              />
            </div>
            <Button onClick={handleAnalyse} size="xl" variant="default" className="w-full mt-6 text-xl">
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
              { icon: Zap, title: 'DeepFake Detector', desc: 'CrossEfficientViT model analyses every keyframe for AI generation artifacts', color: 'bg-clash-3' },
              { icon: Eye, title: 'Source Hunter', desc: 'Reverse image search + EXIF metadata to find the earliest known source', color: 'bg-secondary' },
              { icon: Globe, title: 'Context Analyser', desc: 'Whisper transcription + vision LLM verifies location, language, and timing', color: 'bg-clash-2' },
            ].map((feature) => (
              <Card key={feature.title} className="bk-hover-scale cursor-pointer group">
                <CardHeader className={cn("border-b-4", feature.color)}>
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


    </div>
  );
}
