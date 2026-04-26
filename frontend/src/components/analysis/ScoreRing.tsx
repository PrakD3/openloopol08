'use client';

import { cn } from '@/lib/utils';

interface ScoreRingProps {
  score: number;
  label: string;
  size?: number;
  strokeWidth?: number;
  className?: string;
  colorClass?: string;
}

export function ScoreRing({
  score,
  label,
  size = 120,
  strokeWidth = 10,
  className,
  colorClass = 'text-primary',
}: ScoreRingProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className={cn('flex flex-col items-center gap-2 group', className)}>
      <div
        className="relative border-4 border-foreground bg-background bk-shadow-sm p-1"
        style={{ width: size + 8, height: size + 8 }}
      >
        <svg width={size} height={size} className="rotate-[-90deg]">
          <title>{label} score ring</title>
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            strokeWidth={strokeWidth}
            className="stroke-secondary fill-none"
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="butt"
            className={cn('fill-none transition-all duration-700', colorClass)}
            style={{ stroke: 'currentColor' }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span
            className={cn('text-3xl font-black', colorClass)}
            style={{ textShadow: '3px 3px 0px hsl(var(--foreground))' }}
          >
            {Math.round(score)}
          </span>
        </div>
      </div>
      <span className="text-[10px] font-black uppercase tracking-widest text-foreground text-center mt-1">
        {label}
      </span>
    </div>
  );
}
