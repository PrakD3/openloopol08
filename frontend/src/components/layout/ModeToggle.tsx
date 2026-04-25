'use client';

import { useMode } from '@/hooks/useMode';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { config } from '@/lib/config';
import { AlertTriangle } from 'lucide-react';

export function ModeToggle() {
  const { appMode, inferenceMode, toggleAppMode } = useMode();

  return (
    <div className="flex items-center gap-3">
      <Badge variant={inferenceMode === 'online' ? 'default' : 'secondary'} className="border-2 font-black text-[10px] uppercase tracking-widest px-2">
        {inferenceMode === 'online' ? '🌐 ONLINE' : '📦 OFFLINE'}
      </Badge>
 
      <Button
        variant={appMode === 'real' ? 'destructive' : 'secondary'}
        size="sm"
        onClick={toggleAppMode}
        className="h-8 px-3 font-black text-[10px] uppercase tracking-widest border-2 bk-shadow-sm"
      >
        {appMode === 'demo' ? '🎬 DEMO' : '🔴 REAL'}
      </Button>
 
      {appMode === 'real' && inferenceMode === 'offline' && (
        <div className="flex items-center gap-1.5 text-[10px] font-black uppercase text-destructive bg-destructive/10 border-2 border-destructive px-2 py-0.5">
          <AlertTriangle className="h-3 w-3" />
          <span className="hidden xl:inline">LOCAL MODELS REQ</span>
        </div>
      )}
    </div>
  );
}
