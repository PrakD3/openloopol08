"use client";

import { useState, useCallback } from "react";
import type { AnalysisResult, AgentFinding } from "@/types";
import { sleep } from "@/lib/utils";
import { config } from "@/lib/config";

function ts(): string {
  return new Date().toISOString().replace("T", " ").slice(0, -1);
}

interface UseAnalysisReturn {
  result: AnalysisResult | null;
  isLoading: boolean;
  agentProgress: AgentFinding[];
  error: string | null;
  analyze: (videoUrl: string) => Promise<void>;
  reset: () => void;
}

export function useAnalysis(): UseAnalysisReturn {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [agentProgress, setAgentProgress] = useState<AgentFinding[]>([]);
  const [error, setError] = useState<string | null>(null);

  const reset = useCallback(() => {
    setResult(null);
    setIsLoading(false);
    setAgentProgress([]);
    setError(null);
  }, []);

  const analyze = useCallback(
    async (videoUrl: string) => {
      setIsLoading(true);
      setError(null);
      setResult(null);
      setAgentProgress([]);

      try {
        console.log(
          `[${ts()}] [useAnalysis] Sending POST /api/analyze for URL: ${videoUrl}`,
        );

        const response = await fetch("/api/analyze", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ videoUrl }),
        });

        console.log(
          `[${ts()}] [useAnalysis] Response received — HTTP ${response.status} ${response.statusText}`,
        );

        if (!response.ok) {
          let errorDetail = "(could not read response body)";
          try {
            const errBody = (await response.json()) as { error?: string };
            errorDetail = errBody?.error ?? JSON.stringify(errBody);
          } catch (_) {
            try {
              errorDetail = await response.text();
            } catch (_2) {}
          }
          console.error(
            `[${ts()}] [useAnalysis] Non-OK response (${response.status}): ${errorDetail}`,
          );
          throw new Error(
            `Analysis failed (${response.status}): ${errorDetail}`,
          );
        }

        let data: AnalysisResult;
        try {
          data = (await response.json()) as AnalysisResult;
        } catch (parseErr) {
          console.error(
            `[${ts()}] [useAnalysis] Failed to parse success response JSON:`,
            parseErr,
          );
          throw new Error(
            "Analysis returned an unreadable response. Please try again.",
          );
        }

        console.log(
          `[${ts()}] [useAnalysis] Result received — ` +
            `verdict=${data.verdict}  ` +
            `credibility=${data.credibilityScore}  ` +
            `panic=${data.panicIndex}  ` +
            `agents=${data.agents?.length ?? 0}  ` +
            `flags=${JSON.stringify(data.keyFlags ?? [])}`,
        );

        setResult(data);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "An unexpected error occurred.";
        console.error(`[${ts()}] [useAnalysis] Caught error:`, err);
        setError(message);
      } finally {
        setIsLoading(false);
      }
    },
    [],
  );

  return { result, isLoading, agentProgress, error, analyze, reset };
}
