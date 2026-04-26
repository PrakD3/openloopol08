'use client';

import { useState, useCallback } from 'react';
import type { AnalysisResult, AgentFinding, ModelScore, SOSRegion } from '@/types';
import { DEMO_VIDEOS } from '@/lib/demoData';
import { sleep } from '@/lib/utils';

interface UseAnalysisReturn {
  result: AnalysisResult | null;
  isLoading: boolean;
  agentProgress: AgentFinding[];
  error: string | null;
  analyze: (videoUrl: string, isDemo?: boolean) => Promise<void>;
  reset: () => void;
}

// ---------------------------------------------------------------------------
// Map snake_case backend response → camelCase frontend types
// ---------------------------------------------------------------------------

function mapModelScore(raw: Record<string, unknown>): ModelScore {
  return {
    modelName:    String(raw.model_name   ?? raw.modelName   ?? ''),
    authenticPct: Number(raw.authentic_pct ?? raw.authenticPct ?? 0),
    fakePct:      Number(raw.fake_pct      ?? raw.fakePct      ?? 0),
    confidence:   Number(raw.confidence    ?? 0),
  };
}

function mapAgent(raw: Record<string, unknown>): AgentFinding {
  const modelScoresRaw = (raw.model_scores ?? raw.modelScores ?? []) as Record<string, unknown>[];
  return {
    agentId:              String(raw.agent_id   ?? raw.agentId   ?? ''),
    agentName:            String(raw.agent_name ?? raw.agentName ?? ''),
    status:               (raw.status ?? 'done') as AgentFinding['status'],
    score:                raw.score != null ? Number(raw.score) : null,
    findings:             (raw.findings ?? []) as string[],
    detail:               raw.detail != null ? String(raw.detail) : null,
    duration:             raw.duration_ms != null ? Number(raw.duration_ms) : undefined,
    constraintsSatisfied: raw.constraints_satisfied != null ? Number(raw.constraints_satisfied) : undefined,
    totalConstraints:     raw.total_constraints    != null ? Number(raw.total_constraints)    : undefined,
    constraintDetails:    (raw.constraint_details ?? raw.constraintDetails ?? {}) as Record<string, boolean>,
    modelScores:          modelScoresRaw.map(mapModelScore),
  };
}

function mapSOSRegion(raw: Record<string, unknown> | null | undefined): SOSRegion | null {
  if (!raw) return null;
  return {
    lat:          Number(raw.lat),
    lng:          Number(raw.lng),
    radiusKm:     Number(raw.radius_km ?? raw.radiusKm ?? 0),
    centerName:   String(raw.center_name ?? raw.centerName ?? ''),
    disasterType: String(raw.disaster_type ?? raw.disasterType ?? 'unknown'),
    panicIndex:   Number(raw.panic_index  ?? raw.panicIndex  ?? 0),
    color:        String(raw.color        ?? '#f59e0b'),
    sosActive:    Boolean(raw.sos_active  ?? raw.sosActive   ?? false),
  };
}

function mapResult(raw: Record<string, unknown>): AnalysisResult {
  const agentsRaw = (raw.agents ?? []) as Record<string, unknown>[];
  return {
    jobId:           String(raw.job_id          ?? raw.jobId          ?? ''),
    verdict:         (raw.verdict ?? 'unverified') as AnalysisResult['verdict'],
    credibilityScore: Number(raw.credibility_score ?? raw.credibilityScore ?? 0),
    panicIndex:       Number(raw.panic_index       ?? raw.panicIndex       ?? 5),
    summary:          String(raw.summary ?? ''),
    disasterType:     String(raw.disaster_type ?? raw.disasterType ?? 'unknown'),
    sourceOrigin:     raw.source_origin  != null ? String(raw.source_origin)  : null,
    originalDate:     raw.original_date  != null ? String(raw.original_date)  : null,
    claimedLocation:  raw.claimed_location ?? raw.claimedLocation ?? null,
    actualLocation:   raw.actual_location  ?? raw.actualLocation  ?? null,
    latitude:         raw.latitude         != null ? Number(raw.latitude)  : null,
    longitude:        raw.longitude        != null ? Number(raw.longitude) : null,
    keyFlags:         (raw.key_flags ?? raw.keyFlags ?? []) as string[],
    agents:           agentsRaw.map(mapAgent),
    sosRegion:        mapSOSRegion(raw.sos_region as Record<string, unknown> ?? raw.sosRegion as Record<string, unknown>),
    videoUrl:         raw.video_url != null ? String(raw.video_url) : undefined,
    thumbnail:        raw.thumbnail != null ? String(raw.thumbnail) : undefined,
  };
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

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

  const analyze = useCallback(async (videoUrl: string, isDemo = true) => {
    setIsLoading(true);
    setError(null);
    setResult(null);
    setAgentProgress([]);

    try {
      if (isDemo) {
        const demoVideo = DEMO_VIDEOS.find((v) => v.url === videoUrl) ?? DEMO_VIDEOS[0];
        const precomputed = demoVideo.precomputedResult;

        const initialAgents: AgentFinding[] = precomputed.agents.map((a) => ({
          ...a,
          status: 'idle' as const,
          score: null,
          findings: [],
          detail: null,
          constraintsSatisfied: undefined,
          modelScores: [],
        }));
        setAgentProgress(initialAgents);

        for (let i = 0; i < precomputed.agents.length; i++) {
          setAgentProgress((prev) =>
            prev.map((a, idx) => (idx === i ? { ...a, status: 'running' } : a))
          );
          await sleep((i + 1) * 2500);
          setAgentProgress((prev) =>
            prev.map((a, idx) =>
              idx === i ? { ...precomputed.agents[i], status: 'done' } : a
            )
          );
        }

        await sleep(1000);
        setResult(precomputed);
      } else {
        const response = await fetch('/api/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ videoUrl }),
        });

        if (!response.ok) {
          throw new Error('Analysis failed. Please try again.');
        }

        const raw = await response.json();
        const mapped = mapResult(raw as Record<string, unknown>);
        setResult(mapped);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { result, isLoading, agentProgress, error, analyze, reset };
}
