'use client';

import { useTranslation } from 'react-i18next';
import { CheckCircle2, XCircle, HelpCircle, Megaphone, MapPin } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { MOCK_BULLETINS } from '@/lib/demoData';
import { cn } from '@/lib/utils';
import type { VerdictType } from '@/types';

const VerdictIcon = ({ verdict }: { verdict: VerdictType }) => {
  switch (verdict) {
    case 'real':
      return <CheckCircle2 className="h-4 w-4 text-success" />;
    case 'misleading':
    case 'ai-generated':
      return <XCircle className="h-4 w-4 text-destructive" />;
    case 'unverified':
    default:
      return <HelpCircle className="h-4 w-4 text-muted-foreground" />;
  }
};

export function BulletinBoard() {
  const { t } = useTranslation();

  return (
    <div className="space-y-8">
      <div className="flex items-center gap-4 bg-secondary text-white border-4 border-foreground p-4 bk-shadow-md -rotate-1">
        <Megaphone className="h-8 w-8 text-white" />
        <h2 className="text-3xl font-black uppercase tracking-tighter">{t('bulletin.title')}</h2>
      </div>
      <div className="space-y-6">
        {MOCK_BULLETINS.map((item) => (
          <Card
            key={item.id}
            className={cn(
              'border-4 transition-all bk-hover-scale',
              item.verdict === 'real' && 'bg-secondary/10 border-foreground shadow-bk',
              (item.verdict === 'misleading' || item.verdict === 'ai-generated') && 'bg-destructive/10 border-foreground shadow-bk',
              item.verdict === 'unverified' && 'bg-muted/10 border-foreground shadow-bk'
            )}
          >
            <CardHeader className="p-6 pb-2 border-b-4 border-foreground/10 mb-4">
              <div className="flex items-start gap-4">
                <div className="p-2 border-2 border-foreground bg-background bk-shadow-sm">
                  <VerdictIcon verdict={item.verdict} />
                </div>
                <div className="flex-1 space-y-2">
                  <CardTitle className="text-xl font-black uppercase tracking-tight leading-tight">{item.title}</CardTitle>
                  <div className="flex flex-wrap items-center gap-3 mt-1">
                    <Badge variant={item.verdict as 'real' | 'misleading' | 'unverified'} className="border-2">
                      {t(`verdict.${item.verdict}`).toUpperCase()}
                    </Badge>
                    <span className="text-xs font-black uppercase tracking-widest text-muted-foreground flex items-center gap-1">
                      <MapPin className="h-3 w-3" /> {item.region}
                    </span>
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent className="px-6 pb-6 pt-0">
              <div className="bg-background/50 p-4 border-2 border-foreground/10 bk-noise">
                <p className="text-base font-bold leading-snug">{item.content}</p>
              </div>
              <div className="mt-4 flex justify-between items-center border-t-2 border-foreground/10 pt-4">
                <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">
                  SOURCE: <span className="text-foreground">{item.source.toUpperCase()}</span>
                </p>
                <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">
                  {new Date(item.timestamp).toLocaleDateString()}
                </p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
