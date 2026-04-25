export const config = {
  inferenceMode: 'online',
  appMode: (process.env.NEXT_PUBLIC_APP_MODE as 'demo' | 'real') ?? 'demo',
  backendUrl: process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://127.0.0.1:8000',
  isDemo: process.env.NEXT_PUBLIC_APP_MODE === 'demo',
  isOnline: true,
  isOffline: false,
} as const;
