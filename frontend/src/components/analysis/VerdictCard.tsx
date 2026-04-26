'use client';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn, getVerdictBg, getVerdictColor } from '@/lib/utils';
import type { AnalysisResult } from '@/types';
import { AlertTriangle, Calendar, FileText, MapPin, Share2 } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { ModelBreakdown } from './ModelBreakdown';
import { SOSMap } from './SOSMap';
import { ScoreRing } from './ScoreRing';

interface VerdictCardProps {
  result: AnalysisResult;
}

const DISASTER_EMOJI: Record<string, string> = {
  flood: '🌊',
  earthquake: '🏚️',
  cyclone: '🌀',
  tsunami: '🌊',
  wildfire: '🔥',
  landslide: '⛰️',
  unknown: '⚠️',
};

const FLAG_DISPLAY_MAP: Record<string, string> = {
  API_RESPONSE_ERROR_CONTEXT_ANALYSER: '⚠️ Context verification incomplete',
  API_RESPONSE_ERROR_SOURCE_HUNTER: '⚠️ Source tracing incomplete',
  API_RESPONSE_ERROR_DEEPFAKE: '⚠️ Deepfake analysis incomplete',
};

const displayFlags = (flags: string[]): string[] =>
  flags.filter(Boolean).map((f) => FLAG_DISPLAY_MAP[f] ?? f);

export function VerdictCard({ result }: VerdictCardProps) {
  const { t } = useTranslation();

  const [showUploader, setShowUploader] = useState(false);
  const [showReverseSearch, setShowReverseSearch] = useState(false);
  const [showComments, setShowComments] = useState(false);

  const verdictLabel = t(`verdict.${result.verdict}`);
  const deepfakeAgent = result.agents.find((a) => a.agentId === 'deepfake-detector');
  const hasModelScores = (deepfakeAgent?.modelScores?.length ?? 0) > 0;

  const handleShare = async () => {
    if (!result.jobId) {
      toast.error('Share unavailable — analysis still in progress');
      return;
    }
    const shareUrl = `${window.location.origin}/v/${result.jobId}`;
    try {
      await navigator.clipboard.writeText(shareUrl);
      toast.success('Analysis link copied to clipboard');
    } catch {
      toast.error('Failed to copy link');
    }
  };

  return (
    <div className="space-y-4">
      {/* Main verdict card */}
      <Card className={cn('transition-all', getVerdictBg(result.verdict))}>
        <CardHeader>
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              {/* Disaster type badge */}
              {result.disasterType && result.disasterType !== 'unknown' && (
                <p className="text-xs text-muted-foreground mb-1">
                  {DISASTER_EMOJI[result.disasterType]} Disaster type:{' '}
                  <span className="font-semibold capitalize">{result.disasterType}</span>
                </p>
              )}
              <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">
                {t('analysis.verdict')}
              </p>
              <CardTitle className={cn('text-3xl font-black', getVerdictColor(result.verdict))}>
                {verdictLabel}
              </CardTitle>
            </div>
            <div className="flex items-center gap-4">
              <ScoreRing
                score={result.credibilityScore}
                label={t('analysis.credibilityScore')}
                size={80}
                strokeWidth={6}
                colorClass={
                  result.credibilityScore >= 70
                    ? 'text-success'
                    : result.credibilityScore >= 40
                      ? 'text-accent'
                      : 'text-destructive'
                }
              />
              <ScoreRing
                score={result.panicIndex * 10}
                label={t('analysis.panicIndex')}
                size={80}
                strokeWidth={6}
                colorClass={
                  result.panicIndex >= 7
                    ? 'text-destructive'
                    : result.panicIndex >= 4
                      ? 'text-accent'
                      : 'text-success'
                }
              />
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-5">
          {/* Plain-English summary — black & white style */}
          <div className="rounded-lg border border-border bg-background p-4">
            <div className="flex items-center gap-2 mb-2">
              <FileText className="h-4 w-4 text-muted-foreground" />
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Summary
              </p>
            </div>
            <p className="text-sm leading-relaxed text-foreground font-medium">{result.summary}</p>
          </div>

          {/* Key flags */}
          {result.keyFlags.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {t('analysis.keyFlags')}
              </p>
              <div className="flex flex-wrap gap-2">
                {displayFlags(result.keyFlags).map((flag, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-2 text-xs font-black uppercase tracking-tighter bg-background border-2 border-foreground px-3 py-1.5 bk-shadow-sm"
                  >
                    <AlertTriangle className="h-3.5 w-3.5 text-destructive" />
                    {flag}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Per-model deepfake breakdown */}
          {hasModelScores && <ModelBreakdown modelScores={deepfakeAgent!.modelScores!} />}

          {/* Metadata grid */}
          <div className="grid grid-cols-2 gap-3 text-xs">
            {result.sourceOrigin && (
              <div className="space-y-1">
                <p className="font-medium text-muted-foreground">{t('analysis.sourceOrigin')}</p>
                <a
                  href={result.sourceOrigin}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:underline truncate block"
                >
                  {result.sourceOrigin}
                </a>
              </div>
            )}
            {result.originalDate && (
              <div className="space-y-2">
                <div className="inline-flex items-center gap-1.5 px-2 py-0.5 bg-background border-2 border-foreground text-[10px] font-black uppercase tracking-widest bk-shadow-sm">
                  <Calendar className="h-2.5 w-2.5" /> Original Date
                </div>
                <p className="text-sm font-bold pl-1">{result.originalDate}</p>
              </div>
            )}
            {result.claimedLocation && (
              <div className="space-y-2">
                <div className="inline-flex items-center gap-1.5 px-2 py-0.5 bg-background border-2 border-foreground text-[10px] font-black uppercase tracking-widest bk-shadow-sm">
                  <MapPin className="h-2.5 w-2.5" /> Claimed Location
                </div>
                <p className="text-sm font-bold pl-1">{result.claimedLocation}</p>
              </div>
            )}
            {result.actualLocation && result.actualLocation !== result.claimedLocation && (
              <div className="space-y-2">
                <div className="inline-flex items-center gap-1.5 px-2 py-0.5 bg-background border-2 border-foreground text-[10px] font-black uppercase tracking-widest bk-shadow-sm">
                  <MapPin className="h-2.5 w-2.5" /> Actual Location
                </div>
                <p className="text-sm font-bold pl-1 text-foreground">{result.actualLocation}</p>
              </div>
            )}
          </div>

          <Button onClick={handleShare} variant="outline" size="sm" className="w-full">
            <Share2 className="h-4 w-4 mr-2" />
            {t('analysis.shareResult')}
          </Button>
        </CardContent>
      </Card>

      {/* SOS Map — only when genuine disaster confirmed */}
      {result.sosRegion?.sosActive && (
        <Card className="border-2 border-destructive/40 bg-destructive/5">
          <CardHeader className="pb-2">
            <CardTitle className="text-base text-destructive flex items-center gap-2">
              🆘 SOS Impact Region
            </CardTitle>
          </CardHeader>
          <CardContent>
            <SOSMap sosRegion={result.sosRegion} />
          </CardContent>
        </Card>
      )}

      {/* SOURCE INTELLIGENCE panel */}
      {result.uploaderIntelligence && (
        <Card className="border border-border">
          <CardHeader
            className="pb-2 cursor-pointer select-none"
            onClick={() => setShowUploader(!showUploader)}
          >
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                🕵️ Source Intelligence
              </CardTitle>
              <span className="text-xs text-muted-foreground">{showUploader ? '▲' : '▼'}</span>
            </div>
          </CardHeader>
          {showUploader && (
            <CardContent className="space-y-3 pt-0">
              <div className="flex items-center gap-3">
                <ScoreRing
                  score={result.uploaderIntelligence.trustScore}
                  label="Trust Score"
                  size={72}
                  strokeWidth={6}
                  colorClass={
                    result.uploaderIntelligence.trustScore >= 60
                      ? 'text-accent'
                      : 'text-destructive'
                  }
                />
                <p className="text-sm text-foreground flex-1">
                  {result.uploaderIntelligence.uploaderSummary}
                </p>
              </div>
              {result.uploaderIntelligence.redFlags.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-destructive mb-1">Red Flags</p>
                  <div className="flex flex-wrap gap-1">
                    {result.uploaderIntelligence.redFlags.map((f, i) => (
                      <Badge key={i} variant="destructive" className="text-xs">
                        {f}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
              {result.uploaderIntelligence.trustSignals.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-accent mb-1">Trust Signals</p>
                  <div className="flex flex-wrap gap-1">
                    {result.uploaderIntelligence.trustSignals.map((s, i) => (
                      <Badge key={i} variant="real" className="text-xs">
                        {s}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
              {result.uploaderIntelligence.temporalNote && (
                <p className="text-xs text-muted-foreground italic">
                  {result.uploaderIntelligence.temporalNote}
                </p>
              )}
            </CardContent>
          )}
        </Card>
      )}

      {/* REVERSE SEARCH panel */}
      {result.reverseSearch && (
        <Card className="border border-border">
          <CardHeader
            className="pb-2 cursor-pointer select-none"
            onClick={() => setShowReverseSearch(!showReverseSearch)}
          >
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                🔍 Reverse Search
              </CardTitle>
              <span className="text-xs text-muted-foreground">{showReverseSearch ? '▲' : '▼'}</span>
            </div>
          </CardHeader>
          {showReverseSearch && (
            <CardContent className="space-y-2 pt-0">
              <div className="flex items-center gap-2">
                <span className="text-sm">
                  Prior appearances: <strong>{result.reverseSearch.priorAppearancesCount}</strong>
                </span>
                <Badge
                  variant={
                    result.reverseSearch.temporalDisplacementRisk === 'high'
                      ? 'destructive'
                      : result.reverseSearch.temporalDisplacementRisk === 'medium'
                        ? 'outline'
                        : 'real'
                  }
                  className="text-xs capitalize"
                >
                  {result.reverseSearch.temporalDisplacementRisk} temporal risk
                </Badge>
              </div>
              {result.reverseSearch.bestGuessLabels.length > 0 && (
                <p className="text-xs text-muted-foreground">
                  Identified as: {result.reverseSearch.bestGuessLabels.join(', ')}
                </p>
              )}
              {result.reverseSearch.matchingPages.length > 0 && (
                <div>
                  <p className="text-xs font-semibold mb-1">Matching pages:</p>
                  <ul className="space-y-1">
                    {result.reverseSearch.matchingPages.slice(0, 5).map((page, i) => (
                      <li key={i} className="text-xs">
                        <a
                          href={page.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-primary hover:underline truncate block"
                        >
                          {page.title || page.url}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </CardContent>
          )}
        </Card>
      )}

      {/* COMMUNITY INTELLIGENCE panel */}
      {result.commentIntelligence && (
        <Card className="border border-border">
          <CardHeader
            className="pb-2 cursor-pointer select-none"
            onClick={() => setShowComments(!showComments)}
          >
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                💬 Community Intelligence
              </CardTitle>
              <span className="text-xs text-muted-foreground">{showComments ? '▲' : '▼'}</span>
            </div>
          </CardHeader>
          {showComments && (
            <CardContent className="space-y-2 pt-0">
              <div className="flex items-center gap-2">
                <Badge
                  variant={
                    result.commentIntelligence.communityVerdict === 'confirms_real'
                      ? 'real'
                      : result.commentIntelligence.communityVerdict === 'disputes_authenticity'
                        ? 'destructive'
                        : 'outline'
                  }
                  className="text-xs capitalize"
                >
                  {result.commentIntelligence.communityVerdict.replace(/_/g, ' ')}
                </Badge>
              </div>
              <p className="text-sm text-foreground">
                {result.commentIntelligence.consensusSummary}
              </p>
              {result.commentIntelligence.notableComment && (
                <blockquote className="border-l-2 border-border pl-3 text-xs text-muted-foreground italic">
                  {result.commentIntelligence.notableComment}
                </blockquote>
              )}
            </CardContent>
          )}
        </Card>
      )}
    </div>
  );
}
