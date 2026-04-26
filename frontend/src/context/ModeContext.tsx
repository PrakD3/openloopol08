'use client';

import { config } from '@/lib/config';
import type { AppMode, InferenceMode } from '@/types';
import { createContext, useCallback, useContext, useState } from 'react';

interface ModeContextValue {
  appMode: AppMode;
  inferenceMode: InferenceMode;
  isDemo: boolean;
  isReal: boolean;
  isOnline: boolean;
  isOffline: boolean;
  toggleAppMode: () => void;
}

const ModeContext = createContext<ModeContextValue | null>(null);

export function ModeProvider({ children }: { children: React.ReactNode }) {
  const [appMode, setAppMode] = useState<AppMode>(config.appMode);

  const toggleAppMode = useCallback(() => {
    setAppMode((prev) => (prev === 'demo' ? 'real' : 'demo'));
  }, []);

  return (
    <ModeContext.Provider
      value={{
        appMode,
        inferenceMode: 'online',
        isDemo: appMode === 'demo',
        isReal: appMode === 'real',
        isOnline: true,
        isOffline: false,
        toggleAppMode,
      }}
    >
      {children}
    </ModeContext.Provider>
  );
}

export function useModeContext(): ModeContextValue {
  const ctx = useContext(ModeContext);
  if (!ctx) {
    throw new Error('useModeContext must be used inside <ModeProvider>');
  }
  return ctx;
}
