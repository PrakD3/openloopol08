'use client';

import { useTranslation } from 'react-i18next';
import { Share2, MapPin, Calendar, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScoreRing } from './ScoreRing';
import { cn, getVerdictBg, getVerdictColor } from '@/lib/utils';
import type { AnalysisResult } from '@/types';

interface VerdictCardProps {
  result: AnalysisResult;
}

export function VerdictCard({ result }: VerdictCardProps) {
  const { t } = useTranslation();

  const verdictLabel = t(`verdict.${result.verdict}`);

  const handleShare = () => {
    if (navigator.share) {
      navigator.share({
        title: `Vigilens — ${verdictLabel}`,
        text: result.summary,
        url: window.location.href,
      });
    } else {
      navigator.clipboard.writeText(window.location.href);
    }
  };

  return (
    <Card className={cn('border-4 transition-all bk-noise', result.verdict === 'real' ? 'bg-secondary/20' : 'bg-destructive/10')}>
      <CardHeader className="border-b-4 border-foreground">
        <div className="flex items-center justify-between flex-wrap gap-6">
          <div className="space-y-2">
            <p className="text-xs font-black uppercase tracking-[0.2em] text-foreground bg-background inline-block px-2 py-0.5 border-2 border-foreground">
              {t('analysis.verdict')}
            </p>
            <CardTitle className={cn('text-5xl md:text-6xl font-black uppercase tracking-tighter bk-text-shadow', getVerdictColor(result.verdict))}>
              {verdictLabel}
            </CardTitle>
          </div>
          <div className="flex items-center gap-6">
            <ScoreRing
              score={result.credibilityScore}
              label={t('analysis.credibilityScore')}
              size={80}
              strokeWidth={12}
              colorClass={result.verdict === 'real' ? 'text-clash-3' : 'text-destructive'}
            />
            <ScoreRing
              score={result.panicIndex * 10}
              label={t('analysis.panicIndex')}
              size={80}
              strokeWidth={12}
              colorClass="text-primary"
            />
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-8 pt-8">
        <div className="bg-background border-4 border-foreground p-6 bk-shadow-md">
          <p className="text-lg font-bold leading-tight">{result.summary}</p>
        </div>

        {result.keyFlags.length > 0 && (
          <div className="space-y-3">
            <p className="text-xs font-black uppercase tracking-widest text-muted-foreground flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-destructive" />
              {t('analysis.keyFlags')}
            </p>
            <div className="flex flex-wrap gap-3">
              {result.keyFlags.map((flag, i) => (
                <div key={i} className="flex items-center gap-2 text-sm font-black uppercase bg-destructive text-destructive-foreground border-3 border-foreground px-4 py-2 bk-shadow-sm">
                  {flag}
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            { label: t('analysis.sourceOrigin'), value: result.sourceOrigin, icon: Share2, link: true },
            { label: 'Original Date', value: result.originalDate, icon: Calendar },
            { label: 'Claimed Location', value: result.claimedLocation, icon: MapPin },
            { label: 'Actual Location', value: result.actualLocation, icon: MapPin, destructive: result.actualLocation !== result.claimedLocation },
          ].filter(item => item.value).map((item, i) => (
            <div key={i} className={cn(
              "p-4 border-3 border-foreground bk-shadow-sm space-y-1",
              item.destructive ? "bg-destructive/20" : "bg-background"
            )}>
              <p className={cn("text-[10px] font-black uppercase tracking-widest flex items-center gap-1", item.destructive ? "text-destructive" : "text-muted-foreground")}>
                <item.icon className="h-3 w-3" /> {item.label}
              </p>
              {item.link ? (
                <a href={item.value ?? undefined} target="_blank" rel="noopener noreferrer" className="text-sm font-black uppercase underline decoration-2 underline-offset-4 hover:text-primary truncate block">
                  {item.value}
                </a>
              ) : (
                <p className={cn("text-sm font-black uppercase", item.destructive ? "text-destructive" : "text-foreground")}>{item.value}</p>
              )}
            </div>
          ))}
        </div>

        <Button onClick={handleShare} variant="default" size="xl" className="w-full text-lg">
          <Share2 className="h-5 w-5 mr-3" />
          {t('analysis.shareResult')}
        </Button>
      </CardContent>
    </Card>
  );
}
