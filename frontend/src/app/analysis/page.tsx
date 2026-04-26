"use client";

import { useEffect, useRef, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";
import { Loader2, AlertTriangle, ArrowRight, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AgentPanel } from "@/components/analysis/AgentPanel";
import { VerdictCard } from "@/components/analysis/VerdictCard";
import { LocationMap } from "@/components/analysis/LocationMap";
import { CommunityFeed } from "@/components/community/CommunityFeed";
import { useAnalysis } from "@/hooks/useAnalysis";
import { config } from "@/lib/config";
import { Suspense } from "react";

function AnalysisContent() {
  const { t } = useTranslation();
  const searchParams = useSearchParams();
  const router = useRouter();
  const videoUrl = searchParams.get("url") ?? "";
  const demoParam = searchParams.get("demo");
  const isDemo = demoParam === null ? config.isDemo : demoParam !== "false";

  const { result, isLoading, agentProgress, error, analyze } = useAnalysis();
  const [inputUrl, setInputUrl] = useState("");

  const handleNewAnalysis = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputUrl) return;
    router.push(`/analysis?url=${encodeURIComponent(inputUrl)}&demo=${isDemo}`);
  };
  const displayedAgents = agentProgress.length > 0 ? agentProgress : result?.agents ?? [];

  // Guard against React StrictMode's intentional double-mount in development,
  // which would fire this effect twice and create two backend jobs for one submit.
  const analyzedUrlRef = useRef<string | null>(null);

  useEffect(() => {
    if (videoUrl && analyzedUrlRef.current !== videoUrl) {
      analyzedUrlRef.current = videoUrl;
      analyze(videoUrl, isDemo);
    }
  }, [videoUrl, isDemo, analyze]);

  // When analysis fails, clear the ref so the user can retry the same URL.
  // Without this, the guard above would permanently block re-analysis of a
  // URL that previously errored.
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
              {t("analysis.title")}
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
            {result ? (
              <>
                <VerdictCard result={result} />
                {result.latitude && result.longitude && (
                  <div className="space-y-4">
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
                <CommunityFeed />
              </>
            ) : isLoading ? (
              <div className="flex flex-col items-center justify-center h-[500px] gap-8 border-4 border-foreground bg-secondary/5 bk-diagonal-lines">
                <div className="relative">
                  <div className="absolute inset-0 bg-primary animate-ping opacity-20 border-4 border-foreground" />
                  <Loader2 className="h-24 w-24 animate-spin text-foreground border-4 border-foreground p-4 bg-background bk-shadow-md" />
                </div>
                <div className="text-center space-y-2">
                  <p className="text-3xl font-black uppercase tracking-tighter italic">
                    Running AI pipeline
                  </p>
                  <p className="text-sm font-bold text-muted-foreground uppercase tracking-[0.3em]">
                    Cross-verifying keyframes...
                  </p>
                </div>
              </div>
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
                    Paste a link to a disaster video from Reddit, X, or YouTube to begin forensic verification.
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
                        placeholder={t("home.submitPlaceholder")}
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
                      {t("home.analyseButton")}
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
