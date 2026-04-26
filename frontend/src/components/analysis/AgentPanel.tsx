'use client';

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import type { AgentFinding } from '@/types';
import { CheckCircle2, Clock, Loader2, XCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface AgentPanelProps {
  agents: AgentFinding[];
}

function AgentStatusIcon({ status }: { status: AgentFinding['status'] }) {
  switch (status) {
    case 'running':
      return <Loader2 className="h-4 w-4 animate-spin text-primary" />;
    case 'done':
      return <CheckCircle2 className="h-4 w-4 text-success" />;
    case 'error':
      return <XCircle className="h-4 w-4 text-destructive" />;
    default:
      return <Clock className="h-4 w-4 text-muted-foreground" />;
  }
}

function ConstraintBar({
  satisfied,
  total,
}: {
  satisfied: number;
  total: number;
}) {
  const pct = Math.round((satisfied / total) * 100);
  const isGood = pct >= 70;
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-[10px] font-black uppercase tracking-wider text-muted-foreground">
        <span>
          Constraints: {satisfied}/{total}
        </span>
        <span className={isGood ? 'text-success' : 'text-destructive'}>{pct}%</span>
      </div>
      <div className="h-2 border-2 border-foreground bg-background overflow-hidden p-0.5">
        <div
          className="h-full transition-all duration-700"
          style={{
            width: `${pct}%`,
            backgroundColor: isGood ? 'hsl(var(--success))' : 'hsl(var(--destructive))',
          }}
        />
      </div>
    </div>
  );
}

const getSourceLabel = (agentId: string, score: number, findingsCount: number): string => {
  if (agentId === 'source_hunter' || agentId === 'source-hunter') {
    if (findingsCount <= 2 && score === 0) return 'INSUFFICIENT DATA';
    if (score < 30) return 'LOW CONFIDENCE';
    if (score < 70) return 'PARTIAL CONFIDENCE';
    return `${score.toFixed(1)}% AUTHENTIC`;
  }
  return agentId === 'deepfake-detector' || agentId === 'deepfake_detector'
    ? `${score.toFixed(1)}% FAKE`
    : `${score.toFixed(1)}% AUTHENTIC`;
};

export function AgentPanel({ agents }: AgentPanelProps) {
  const { t } = useTranslation();

  return (
    <div className="space-y-4">
      <h3 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">
        {t('analysis.agents')}
      </h3>

      <Accordion type="multiple" className="space-y-4">
        {agents.map((agent, index) => {
          const isDeepfake =
            agent.agentId === 'deepfake-detector' || agent.agentId === 'deepfake_detector';
          const isSource = agent.agentId === 'source-hunter' || agent.agentId === 'source_hunter';
          const scorePct = agent.score ?? 0;
          const badgeDestructive = isDeepfake
            ? scorePct > 50
            : isSource && agent.findings.length <= 2 && scorePct === 0
              ? false
              : scorePct < 50;

          return (
            <AccordionItem
              key={agent.agentId}
              value={agent.agentId}
              className="border-3 border-foreground shadow-[4px_4px_0px_hsl(var(--shadow-color))]"
            >
              <AccordionTrigger className="hover:no-underline py-3 px-4">
                <div className="flex items-center gap-2 flex-1">
                  <div className="text-foreground">
                    <AgentStatusIcon status={agent.status} />
                  </div>
                  <span className="text-[11px] font-black uppercase tracking-tight text-left text-foreground">
                    Agent Analysis {index + 1} (
                    {agent.agentId.includes('deepfake')
                      ? 'DEEPFAKE'
                      : agent.agentId.includes('source')
                        ? 'SOURCE'
                        : agent.agentId.includes('context')
                          ? 'CONTEXT'
                          : agent.agentId.includes('geo')
                            ? 'GEOLOCATION'
                            : agent.agentName || 'GENERAL'}
                    )
                  </span>
                </div>

                {agent.score !== null && agent.score !== undefined && (
                  <div className="shrink-0 mr-2">
                    <Badge
                      variant={badgeDestructive ? 'destructive' : 'real'}
                      className="text-[9px] px-1.5 py-0.5 border-2 font-black bg-background text-foreground"
                    >
                      {getSourceLabel(agent.agentId, scorePct, agent.findings.length)}
                    </Badge>
                  </div>
                )}
              </AccordionTrigger>

              <AccordionContent className="bg-background pt-4 border-t-3 border-foreground">
                {agent.status === 'running' && (
                  <Progress value={undefined} className="h-1.5 animate-pulse mb-2" />
                )}

                {agent.status === 'done' && (
                  <div className="space-y-4">
                    {/* Constraint bar */}
                    {agent.constraintsSatisfied !== undefined &&
                      agent.totalConstraints !== undefined && (
                        <ConstraintBar
                          satisfied={agent.constraintsSatisfied}
                          total={agent.totalConstraints}
                        />
                      )}

                    {/* Findings */}
                    {agent.findings.length > 0 && (
                      <ul className="space-y-2">
                        {agent.findings.map((finding, i) => (
                          <li
                            key={i}
                            className="text-xs text-foreground font-medium flex items-start gap-2"
                          >
                            <span className="text-success font-black mt-0.5">●</span>
                            {finding}
                          </li>
                        ))}
                      </ul>
                    )}

                    {/* Per-model scores for deepfake agent */}
                    {isDeepfake && agent.modelScores && agent.modelScores.length > 0 && (
                      <div className="mt-4 space-y-2 border-t-2 border-foreground pt-3">
                        <p className="text-[10px] text-muted-foreground font-black uppercase tracking-wider">
                          Model Breakdown:
                        </p>
                        {agent.modelScores.map((m) => (
                          <div
                            key={m.modelName}
                            className="flex items-center justify-between text-[10px] font-bold"
                          >
                            <span className="text-muted-foreground uppercase">{m.modelName}</span>
                            <span
                              className={m.authenticPct >= 50 ? 'text-success' : 'text-destructive'}
                            >
                              {m.authenticPct.toFixed(1)}% AUTH / {m.fakePct.toFixed(1)}% FAKE
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </AccordionContent>
            </AccordionItem>
          );
        })}
      </Accordion>
    </div>
  );
}
