export const config = {
  inferenceMode: (process.env.NEXT_PUBLIC_INFERENCE_MODE as 'online' | 'offline') ?? 'online',
  appMode: (process.env.NEXT_PUBLIC_APP_MODE as 'demo' | 'real') ?? 'demo',
  backendUrl: process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://127.0.0.1:8000',
  isDemo: process.env.NEXT_PUBLIC_APP_MODE === 'demo',
  isOnline: process.env.NEXT_PUBLIC_INFERENCE_MODE !== 'offline',
  isOffline: process.env.NEXT_PUBLIC_INFERENCE_MODE === 'offline',
} as const;
