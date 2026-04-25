'use client';

import { createContext, useCallback, useContext, useState } from 'react';
import { config } from '@/lib/config';
import type { AppMode, InferenceMode } from '@/types';

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
  const [appMode] = useState<AppMode>('real');
  const [inferenceMode] = useState<InferenceMode>('online');

  const toggleAppMode = useCallback(() => {
    // No-op in production
  }, []);

  return (
    <ModeContext.Provider
      value={{
        appMode,
        inferenceMode,
        isDemo: false,
        isReal: true,
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
