'use client';

import { AgentPanel } from '@/components/analysis/AgentPanel';
import { LocationMap } from '@/components/analysis/LocationMap';
import { VerdictCard } from '@/components/analysis/VerdictCard';
import { CommunityFeed } from '@/components/community/CommunityFeed';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAnalysis } from '@/hooks/useAnalysis';
import { config } from '@/lib/config';
import { AlertTriangle, ArrowRight, Loader2, Shield } from 'lucide-react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { Suspense } from 'react';
import { useTranslation } from 'react-i18next';

import { MatrixLoader } from '@/components/analysis/MatrixLoader';

function AnalysisContent() {
  const { t } = useTranslation();
  const searchParams = useSearchParams();
  const router = useRouter();
  const videoUrl = searchParams.get('url') ?? '';
  const demoParam = searchParams.get('demo');
  const isDemo = demoParam === null ? config.isDemo : demoParam !== 'false';

  const { result, isLoading, agentProgress, error, analyze } = useAnalysis();
  const [inputUrl, setInputUrl] = useState('');
  const [showResults, setShowResults] = useState(false);

  // When isLoading becomes false and result is present, wait for MatrixLoader animation
  useEffect(() => {
    if (!isLoading && result) {
      // setShowResults(true) is now handled by MatrixLoader's onAnimationComplete
    } else {
      setShowResults(false);
    }
  }, [isLoading, result]);

  const handleNewAnalysis = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputUrl) return;
    router.push(`/analysis?url=${encodeURIComponent(inputUrl)}&demo=${isDemo}`);
  };
  const displayedAgents = agentProgress.length > 0 ? agentProgress : (result?.agents ?? []);

  // Guard against React StrictMode's intentional double-mount in development
  const analyzedUrlRef = useRef<string | null>(null);

  useEffect(() => {
    if (videoUrl && analyzedUrlRef.current !== videoUrl) {
      analyzedUrlRef.current = videoUrl;
      analyze(videoUrl, isDemo);
    }
  }, [videoUrl, isDemo, analyze]);

  useEffect(() => {
    if (error) {
      analyzedUrlRef.current = null;
    }
  }, [error]);

  return (
    <div className="min-h-screen py-12 px-4 bg-background bk-noise">
      <div className="mx-auto max-w-7xl">
        <div className="flex flex-col md:flex-row items-start md:items-end gap-4 mb-12">
          <div className="p-3 bg-primary border-4 border-foreground bk-shadow-md">
            <h1 className="text-4xl md:text-6xl font-black uppercase tracking-tighter leading-none text-primary-foreground">
              {t('analysis.title')}
            </h1>
          </div>
          {videoUrl && (
            <p className="text-xs font-black uppercase tracking-widest text-muted-foreground border-3 border-foreground p-2 bg-background bk-shadow-sm truncate max-w-md">
              ANALYSING: {videoUrl}
            </p>
          )}
        </div>

        {error && (
          <div className="mb-8 p-6 border-4 border-foreground bg-destructive/10 text-destructive font-black uppercase tracking-widest bk-shadow-md flex items-center gap-3">
            <AlertTriangle className="h-6 w-6" />
            {error}
          </div>
        )}

        <div className="grid lg:grid-cols-12 gap-8">
          <div className="lg:col-span-4">
            {isLoading || displayedAgents.length > 0 ? (
              <AgentPanel agents={displayedAgents} />
            ) : !result ? (
              <div className="flex items-center gap-4 p-6 border-4 border-foreground bg-muted/20 bk-shadow-sm">
                <span className="font-black uppercase tracking-widest opacity-40">
                  Waiting for input
                </span>
              </div>
            ) : null}
          </div>

          <div className="lg:col-span-8 space-y-8">
            {result && showResults ? (
              <div className="animate-in fade-in zoom-in-95 duration-1000 slide-in-from-bottom-10">
                <VerdictCard result={result} />
                {result.latitude && result.longitude && (
                  <div className="space-y-4 mt-8">
                    <div className="p-3 bg-secondary border-4 border-foreground bk-shadow-sm inline-block">
                      <h3 className="text-xl font-black uppercase tracking-tighter leading-none">
                        Geographical Verification
                      </h3>
                    </div>
                    <LocationMap
                      latitude={result.latitude}
                      longitude={result.longitude}
                      label={result.actualLocation || 'Confirmed Location'}
                    />
                  </div>
                )}
                <div className="mt-8">
                  <CommunityFeed />
                </div>
              </div>
            ) : isLoading || (result && !showResults) ? (
              <MatrixLoader
                videoUrl={videoUrl}
                isComplete={!isLoading && !!result}
                onAnimationComplete={() => setShowResults(true)}
              />
            ) : (
              <div className="h-[600px] border-4 border-foreground bg-secondary/5 flex flex-col items-center justify-center p-8 text-center space-y-8 bk-diagonal-lines">
                <div className="space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-700">
                  <div className="mx-auto w-20 h-20 bg-background border-4 border-foreground flex items-center justify-center bk-shadow-sm mb-6 rotate-3">
                    <Shield className="h-10 w-10 text-primary" />
                  </div>
                  <h2 className="text-4xl md:text-5xl font-black uppercase tracking-tighter italic leading-none">
                    Ready for Analysis
                  </h2>
                  <p className="text-base font-bold text-muted-foreground uppercase tracking-widest max-w-md mx-auto">
                    Paste a link to a disaster video from Reddit, X, or YouTube to begin forensic
                    verification.
                  </p>
                </div>

                <form
                  onSubmit={handleNewAnalysis}
                  className="w-full max-w-lg space-y-4 animate-in fade-in slide-in-from-bottom-8 duration-1000"
                >
                  <div className="flex flex-col gap-4 p-6 bg-background border-4 border-foreground bk-shadow-lg">
                    <div className="space-y-2 text-left mb-2">
                      <label className="text-xs font-black uppercase tracking-[0.2em] text-muted-foreground">
                        Target Source URL
                      </label>
                      <Input
                        type="url"
                        placeholder={t('home.submitPlaceholder')}
                        value={inputUrl}
                        onChange={(e) => setInputUrl(e.target.value)}
                        className="text-lg h-14 bg-muted/20"
                        required
                      />
                    </div>
                    <Button
                      type="submit"
                      size="xl"
                      className="w-full text-xl font-black uppercase tracking-widest"
                    >
                      {t('home.analyseButton')}
                      <ArrowRight className="ml-2 h-6 w-6" />
                    </Button>
                  </div>
                </form>

                <div className="flex items-center gap-6 opacity-30 animate-pulse">
                  <div className="h-[2px] w-12 bg-foreground" />
                  <span className="text-[10px] font-black uppercase tracking-[0.4em]">
                    Awaiting Signal
                  </span>
                  <div className="h-[2px] w-12 bg-foreground" />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function AnalysisPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-background bk-noise">
          <Loader2 className="h-12 w-12 animate-spin text-primary" />
        </div>
      }
    >
      <AnalysisContent />
    </Suspense>
  );
}
