'use client';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { MOCK_INCIDENTS } from '@/lib/demoData';
import { cn } from '@/lib/utils';
import type { VerdictType } from '@/types';
import { MapPin } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

const filters: Array<{ label: string; value: string }> = [
  { label: 'All', value: 'all' },
  { label: 'Real', value: 'real' },
  { label: 'Misleading', value: 'misleading' },
  { label: 'AI Generated', value: 'ai-generated' },
  { label: 'Unverified', value: 'unverified' },
];

export default function IncidentsPage() {
  const { t } = useTranslation();
  const [activeFilter, setActiveFilter] = useState('all');

  const filtered = MOCK_INCIDENTS.filter(
    (i) => activeFilter === 'all' || i.verdict === activeFilter
  );

  return (
    <div className="min-h-screen py-12 px-4 bg-background bk-noise">
      <div className="mx-auto max-w-7xl">
        <div className="mb-12 border-l-8 border-foreground pl-6">
          <h1 className="text-4xl md:text-6xl font-black uppercase tracking-tighter italic">
            {t('incidents.title')}
          </h1>
          <p className="text-lg font-bold text-muted-foreground mt-2 uppercase tracking-widest">
            Verification logs tracked by Vigilens Intelligence
          </p>
        </div>

        <div className="flex gap-4 flex-wrap mb-12">
          {filters.map((f) => (
            <Button
              key={f.value}
              variant={activeFilter === f.value ? 'default' : 'outline'}
              size="lg"
              className={cn(
                'border-3 transition-all',
                activeFilter === f.value
                  ? 'bk-shadow-sm translate-x-[2px] translate-y-[2px] shadow-none'
                  : 'bk-shadow-md'
              )}
              onClick={() => setActiveFilter(f.value)}
            >
              {f.label.toUpperCase()}
            </Button>
          ))}
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {filtered.map((incident) => (
            <Card key={incident.id} className="border-4 shadow-bk bk-hover-scale cursor-pointer">
              <CardHeader className="pb-4 bg-muted/20 border-b-4">
                <div className="flex items-center justify-between mb-4">
                  <Badge variant={incident.verdict as VerdictType} className="border-2">
                    {incident.verdict.toUpperCase()}
                  </Badge>
                  <span className="text-xs font-black uppercase tracking-tighter italic">
                    {incident.date}
                  </span>
                </div>
                <CardTitle className="text-lg font-black uppercase leading-tight tracking-tight">
                  {incident.title}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6 pt-6">
                <div className="space-y-4">
                  <p className="text-xs font-black uppercase tracking-widest text-muted-foreground flex items-center gap-2">
                    <MapPin className="h-3 w-3" /> {incident.location}
                  </p>
                  <p className="text-sm font-bold leading-snug p-3 border-2 border-foreground/10 bg-secondary/5">
                    {incident.summary}
                  </p>
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between items-end mb-1">
                    <span className="text-[10px] font-black uppercase tracking-widest">
                      {t('incidents.misinfoRate')}
                    </span>
                    <span className="text-lg font-black text-destructive">
                      {incident.misinfoRate}%
                    </span>
                  </div>
                  <div className="h-4 bg-background border-3 border-foreground overflow-hidden bk-shadow-sm">
                    <div
                      className="h-full bg-destructive border-r-3 border-foreground transition-all"
                      style={{ width: `${incident.misinfoRate}%` }}
                    />
                  </div>
                </div>

                <div className="flex flex-wrap gap-2 pt-2">
                  {incident.tags.map((tag) => (
                    <span
                      key={tag}
                      className="text-[10px] font-black uppercase tracking-[0.2em] bg-secondary text-white px-3 py-1 border-2 border-foreground bk-shadow-sm"
                    >
                      #{tag}
                    </span>
                  ))}
                </div>

                <div className="pt-4 border-t-2 border-foreground/10 flex justify-between items-center">
                  <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">
                    {t('incidents.videoCount')}: {incident.videoCount} SAMPLES
                  </p>
                  <div className="h-2 w-2 rounded-full bg-primary animate-pulse" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
