'use client';

import type { ModelScore } from '@/types';

interface ModelBreakdownProps {
  modelScores: ModelScore[];
}

const MODEL_ICONS: Record<string, string> = {
  'Vertex AI (Gemini)': '♊',
  'Groq Vision (Llama)': '🦙',
};

export function ModelBreakdown({ modelScores }: ModelBreakdownProps) {
  if (!modelScores || modelScores.length === 0) return null;

  return (
    <div className="space-y-3">
      <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
        Detection Model Breakdown
      </p>
      <div className="grid gap-2">
        {modelScores.map((m) => {
          const isAuthentic = m.authenticPct >= 50;
          return (
            <div
              key={m.modelName}
              className="rounded-lg border border-border bg-secondary/30 px-4 py-3 flex items-center justify-between gap-4"
            >
              {/* Model name */}
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-base">{MODEL_ICONS[m.modelName] ?? '📊'}</span>
                <span className="text-sm font-medium truncate">{m.modelName}</span>
              </div>

              {/* Bar + percentages */}
              <div className="flex-1 max-w-[180px]">
                <div className="flex justify-between text-xs text-muted-foreground mb-1">
                  <span className="text-green-600 dark:text-green-400">
                    {m.authenticPct.toFixed(1)}% auth
                  </span>
                  <span className="text-red-500">{m.fakePct.toFixed(1)}% fake</span>
                </div>
                <div className="h-2 rounded-full bg-secondary overflow-hidden">
                  {/* Green = authentic portion */}
                  <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{
                      width: `${m.authenticPct}%`,
                      background: isAuthentic
                        ? 'linear-gradient(90deg, #22c55e, #16a34a)'
                        : 'linear-gradient(90deg, #ef4444, #dc2626)',
                    }}
                  />
                </div>
              </div>

              {/* Confidence badge */}
              <span className="text-xs text-muted-foreground whitespace-nowrap">
                {m.confidence.toFixed(0)}% conf.
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
