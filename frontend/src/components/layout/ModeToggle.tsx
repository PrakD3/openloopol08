'use client';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useMode } from '@/hooks/useMode';

export function ModeToggle() {
  const { appMode, toggleAppMode } = useMode();

  return (
    <div className="flex items-center gap-3">
      <Badge
        variant="default"
        className="border-2 font-black text-[10px] uppercase tracking-widest px-2"
      >
        🌐 ONLINE
      </Badge>

      <Button
        variant={appMode === 'real' ? 'destructive' : 'secondary'}
        size="sm"
        onClick={toggleAppMode}
        className="h-8 px-3 font-black text-[10px] uppercase tracking-widest border-2 bk-shadow-sm"
      >
        {appMode === 'demo' ? '🎬 DEMO' : '🔴 REAL'}
      </Button>
    </div>
  );
}
