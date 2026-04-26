"use client";

import { useTranslation } from "react-i18next";
import { CheckCircle2, Loader2, XCircle, Clock } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import type { AgentFinding } from "@/types";

interface AgentPanelProps {
  agents: AgentFinding[];
}

function AgentStatusIcon({ status }: { status: AgentFinding["status"] }) {
  switch (status) {
    case "running":
      return <Loader2 className="h-4 w-4 animate-spin text-primary" />;
    case "done":
      return <CheckCircle2 className="h-4 w-4 text-accent" />;
    case "error":
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
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>
          Constraints: {satisfied}/{total}
        </span>
        <span className={isGood ? "text-green-500" : "text-red-400"}>
          {pct}%
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-secondary overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{
            width: `${pct}%`,
            background: isGood
              ? "linear-gradient(90deg, #22c55e, #16a34a)"
              : "linear-gradient(90deg, #ef4444, #dc2626)",
          }}
        />
      </div>
    </div>
  );
}

const getSourceLabel = (
  agentId: string,
  score: number,
  findingsCount: number,
): string => {
  if (agentId === "source_hunter") {
    if (findingsCount <= 2 && score === 0) return "INSUFFICIENT DATA";
    if (score < 30) return "LOW CONFIDENCE";
    if (score < 70) return "PARTIAL CONFIDENCE";
    return `${score.toFixed(1)}% AUTHENTIC`;
  }
  return agentId === "deepfake-detector"
    ? `${score.toFixed(1)}% fake`
    : `${score.toFixed(1)}% authentic`;
};

export function AgentPanel({ agents }: AgentPanelProps) {
  const { t } = useTranslation();

  return (
    <div className="space-y-3">
      <h3 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">
        {t("analysis.agents")}
      </h3>
      {agents.map((agent) => {
        const isDeepfake = agent.agentId === "deepfake-detector" || agent.agentId === "deepfake_detector";
        const isSource = agent.agentId === "source-hunter" || agent.agentId === "source_hunter";
        // For deepfake: score = fake%, lower is better → badge shows fake%
        // For others: score = authenticity%, higher is better
        const scorePct = agent.score ?? 0;
        const badgeDestructive = isDeepfake
          ? scorePct > 50
          : isSource && agent.findings.length <= 2 && scorePct === 0
            ? false
            : scorePct < 50;

        return (
          <Card
            key={agent.agentId}
            className={cn(
              "transition-all duration-300",
              agent.status === "running" && "border-primary/50 shadow-sm",
              agent.status === "done" && "border-accent/30",
            )}
          >
            <CardHeader className="p-4 pb-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AgentStatusIcon status={agent.status} />
                  <CardTitle className="text-sm font-black uppercase tracking-tight">{agent.agentName}</CardTitle>
                </div>
                {agent.score !== null && agent.score !== undefined && (
                  <Badge
                    variant={badgeDestructive ? "destructive" : "real"}
                    className="text-xs"
                  >
                    {getSourceLabel(
                      agent.agentId,
                      scorePct,
                      agent.findings.length,
                    )}
                  </Badge>
                )}
              </div>
            </CardHeader>

            {agent.status === "running" && (
              <CardContent className="px-4 pb-4 pt-0">
                <Progress value={undefined} className="h-1 animate-pulse" />
              </CardContent>
            )}

            {agent.status === "done" && (
              <CardContent className="px-4 pb-4 pt-0 space-y-3">
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
                  <ul className="space-y-1">
                    {agent.findings.slice(0, 4).map((finding, i) => (
                      <li
                        key={i}
                        className="text-xs text-muted-foreground flex items-start gap-1.5"
                      >
                        <span className="text-accent mt-0.5">•</span>
                        {finding}
                      </li>
                    ))}
                  </ul>
                )}

                {/* Per-model scores for deepfake agent */}
                {isDeepfake &&
                  agent.modelScores &&
                  agent.modelScores.length > 0 && (
                    <div className="mt-2 space-y-1.5 border-t border-border pt-2">
                      <p className="text-xs text-muted-foreground font-medium">
                        Per model:
                      </p>
                      {agent.modelScores.map((m) => (
                        <div
                          key={m.modelName}
                          className="flex items-center justify-between text-xs"
                        >
                          <span className="text-muted-foreground">
                            {m.modelName}
                          </span>
                          <span
                            className={
                              m.authenticPct >= 50
                                ? "text-green-500 font-medium"
                                : "text-red-400 font-medium"
                            }
                          >
                            {m.authenticPct.toFixed(1)}% auth /{" "}
                            {m.fakePct.toFixed(1)}% fake
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
              </CardContent>
            )}
          </Card>
        );
      })}
    </div>
  );
}
