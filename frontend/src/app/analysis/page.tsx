"use client";

import { useEffect, useRef } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslation } from "react-i18next";
import { Loader2, AlertTriangle } from "lucide-react";
import { AgentPanel } from "@/components/analysis/AgentPanel";
import { VerdictCard } from "@/components/analysis/VerdictCard";
import { CommunityFeed } from "@/components/community/CommunityFeed";
import { useAnalysis } from "@/hooks/useAnalysis";
import { config } from "@/lib/config";
import { Suspense } from "react";

function AnalysisContent() {
  const { t } = useTranslation();
  const searchParams = useSearchParams();
  const videoUrl = searchParams.get("url") ?? "";
  const isDemo = false;

  const { result, isLoading, agentProgress, error, analyze } = useAnalysis();
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
            <h1 className="text-4xl md:text-6xl font-black uppercase tracking-tighter leading-none">
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
                <Loader2 className="h-8 w-8 animate-spin text-foreground" />
                <span className="font-black uppercase tracking-widest">
                  Initialising agents...
                </span>
              </div>
            ) : null}
          </div>

          <div className="lg:col-span-8 space-y-8">
            {result ? (
              <>
                <VerdictCard result={result} />
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
              <div className="h-[500px] border-4 border-foreground bg-muted/10 flex items-center justify-center">
                <p className="font-black uppercase tracking-widest opacity-20 text-4xl -rotate-12">
                  Waiting for input
                </p>
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
