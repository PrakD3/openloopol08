import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatScore(score: number): string {
  return `${Math.round(score)}%`;
}

export function getVerdictColor(verdict: string): string {
  switch (verdict) {
    case 'real':
      return 'text-accent';
    case 'misleading':
      return 'text-destructive';
    case 'ai-generated':
      return 'text-primary';
    default:
      return 'text-muted-foreground';
  }
}

export function getVerdictBg(verdict: string): string {
  switch (verdict) {
    case 'real':
      return 'bg-accent/10 border-accent/30';
    case 'misleading':
      return 'bg-destructive/10 border-destructive/30';
    case 'ai-generated':
      return 'bg-primary/10 border-primary/30';
    default:
      return 'bg-muted border-border';
  }
}

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
