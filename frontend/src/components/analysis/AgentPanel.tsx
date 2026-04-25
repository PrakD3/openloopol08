'use client';

import { useTranslation } from 'react-i18next';
import { CheckCircle2, Loader2, XCircle, Clock } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';
import type { AgentFinding } from '@/types';

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

export function AgentPanel({ agents }: AgentPanelProps) {
  const { t } = useTranslation();

  return (
    <div className="space-y-4">
      <h3 className="font-black text-xs text-foreground uppercase tracking-[0.2em] bg-secondary text-white inline-block px-3 py-1 border-3 border-foreground bk-shadow-sm mb-2">
        {t('analysis.agents')}
      </h3>
      {agents.map((agent) => (
        <Card
          key={agent.agentId}
          className={cn(
            'transition-all duration-300 border-4',
            agent.status === 'running' && 'border-primary ring-4 ring-primary/20',
            agent.status === 'done' && 'border-foreground shadow-bk'
          )}
        >
          <CardHeader className={cn("p-4 pb-2 border-b-4", agent.status === 'running' ? 'bg-primary/10' : 'bg-muted/30')}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-1 border-2 border-foreground bg-background bk-shadow-sm">
                  <AgentStatusIcon status={agent.status} />
                </div>
                <CardTitle className="text-sm font-black uppercase tracking-tight">{agent.agentName}</CardTitle>
              </div>
              {agent.score !== null && (
                <Badge variant={agent.score > 50 ? 'destructive' : 'real'} className="border-2">
                  {agent.agentId === 'deepfake-detector' || agent.agentId === 'deepfake_detector'
                    ? `${agent.score}% FAKE`
                    : `${agent.score}% AUTHENTIC`}
                </Badge>
              )}
            </div>
          </CardHeader>
          {agent.status === 'running' && (
            <CardContent className="px-4 pb-4 pt-4">
              <Progress value={undefined} className="animate-pulse" />
            </CardContent>
          )}
          {agent.status === 'done' && agent.findings.length > 0 && (
            <CardContent className="px-4 pb-4 pt-4">
              <ul className="space-y-2">
                {agent.findings.map((finding, i) => (
                  <li key={i} className="text-xs font-bold text-foreground flex items-start gap-2 bg-secondary/10 p-2 border-2 border-foreground/20">
                    <span className="text-primary font-black mt-0.5">»</span>
                    {finding}
                  </li>
                ))}
              </ul>
            </CardContent>
          )}
        </Card>
      ))}
    </div>
  );
}
