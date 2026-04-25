export const config = {
  inferenceMode: 'online',
  appMode: 'real',
  backendUrl: process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://127.0.0.1:8000',
  isDemo: false,
  isOnline: true,
  isOffline: false,
} as const;
