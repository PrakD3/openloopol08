'use client';

import { DEMO_VIDEOS } from '@/lib/demoData';
import { cn } from '@/lib/utils';
import { AnimatePresence, motion } from 'framer-motion';
import { useEffect, useState } from 'react';

interface MatrixLoaderProps {
  videoUrl: string;
  isComplete: boolean;
  onAnimationComplete?: () => void;
}

export function MatrixLoader({ videoUrl, isComplete, onAnimationComplete }: MatrixLoaderProps) {
  const [thumbnail, setThumbnail] = useState<string | null>(null);
  const [isPortrait, setIsPortrait] = useState(false);

  useEffect(() => {
    // Extract thumbnail
    const demo = DEMO_VIDEOS.find((v) => v.url === videoUrl);
    if (demo) {
      setThumbnail(demo.thumbnail);
    } else {
      // Improved YouTube Regex
      const ytMatch = videoUrl.match(
        /(?:https?:\/\/)?(?:www\.)?(?:youtube\.com|youtu\.be)\/(?:watch\?v=)?(?:embed\/)?(?:v\/)?(?:shorts\/)?([^?&"'>]+)/
      );
      if (ytMatch && ytMatch[1]) {
        // Use hqdefault as maxresdefault isn't always available
        setThumbnail(`https://img.youtube.com/vi/${ytMatch[1]}/hqdefault.jpg`);
      } else {
        // Default forensic placeholder for Reddit, X, etc.
        setThumbnail('/images/forensic-placeholder.png');
      }
    }
  }, [videoUrl]);

  const handleImageLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    const { naturalWidth, naturalHeight } = e.currentTarget;
    setIsPortrait(naturalHeight > naturalWidth);
  };

  return (
    <div className="relative w-full h-[500px] bg-black overflow-hidden border-4 border-foreground bk-shadow-lg flex items-center justify-center">
      {/* Background Matrix Grid */}
      <div className="absolute inset-0 z-0 opacity-20">
        <div
          className="w-full h-full"
          style={{
            backgroundImage: `linear-gradient(to right, #444 1px, transparent 1px), linear-gradient(to bottom, #444 1px, transparent 1px)`,
            backgroundSize: '20px 20px',
          }}
        />
      </div>

      {/* Dynamic Grid Box Overlay */}
      <motion.div
        className="absolute inset-0 z-10 border-2 border-primary/30"
        animate={{
          backgroundPosition: ['0% 0%', '100% 100%'],
        }}
        transition={{
          duration: 20,
          repeat: Number.POSITIVE_INFINITY,
          ease: 'linear',
        }}
        style={{
          backgroundImage: `radial-gradient(circle at center, transparent 0%, rgba(0,0,0,0.4) 100%)`,
        }}
      />

      {/* Thumbnail Container */}
      <div className="relative z-20 w-full h-full flex items-center justify-center p-4">
        <AnimatePresence mode="wait">
          {!isComplete ? (
            <motion.div
              key="loader-content"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{
                scale: 5,
                opacity: 0,
                transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] },
              }}
              className="relative w-full h-full flex flex-col items-center justify-center"
            >
              {thumbnail ? (
                <div
                  className={cn(
                    'relative border-4 border-foreground bk-shadow-md overflow-hidden bg-muted',
                    isPortrait ? 'h-[80%] aspect-[9/16]' : 'w-full h-full'
                  )}
                >
                  <img
                    src={thumbnail}
                    alt="Source Preview"
                    onLoad={handleImageLoad}
                    className={cn(
                      'w-full h-full object-cover',
                      !isPortrait && 'scale-110' // Slight stretch/zoom for landscape as requested
                    )}
                  />
                  {/* Platform Badge */}
                  <div className="absolute top-4 left-4 z-40 bg-foreground text-background px-3 py-1 text-[10px] font-black uppercase tracking-widest border-2 border-primary shadow-[0_0_10px_rgba(var(--primary),0.5)]">
                    {videoUrl.includes('youtube.com') || videoUrl.includes('youtu.be') ? 'Source: YouTube' : 
                     videoUrl.includes('reddit.com') ? 'Source: Reddit' :
                     videoUrl.includes('twitter.com') || videoUrl.includes('x.com') ? 'Source: X / Twitter' :
                     'Source: External Link'}
                  </div>
                  {/* Scanning Line */}
                  <motion.div
                    className="absolute top-0 left-0 w-full h-1 bg-primary z-30 shadow-[0_0_15px_rgba(var(--primary),0.8)]"
                    animate={{ top: ['0%', '100%'] }}
                    transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY, ease: 'linear' }}
                  />
                  {/* Glitch Overlay */}
                  <div className="absolute inset-0 pointer-events-none mix-blend-overlay opacity-30 bk-diagonal-lines" />
                </div>
              ) : (
                <div className="w-48 h-48 border-4 border-foreground flex items-center justify-center bg-background">
                  <div className="w-12 h-12 border-4 border-primary border-t-transparent animate-spin" />
                </div>
              )}

              <div className="absolute bottom-12 left-1/2 -translate-x-1/2 text-center space-y-2 bg-background/90 p-4 border-4 border-foreground bk-shadow-sm min-w-[300px]">
                <p className="text-3xl font-black uppercase tracking-tighter italic text-foreground">
                  Running AI pipeline
                </p>
                <div className="flex items-center justify-center gap-4">
                  <div className="h-1 w-12 bg-primary" />
                  <p className="text-xs font-bold text-muted-foreground uppercase tracking-[0.3em]">
                    Forensic Sweep In Progress
                  </p>
                  <div className="h-1 w-12 bg-primary" />
                </div>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="complete-flash"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              onAnimationComplete={onAnimationComplete}
              className="absolute inset-0 bg-primary z-50 flex items-center justify-center"
            >
              <h2 className="text-8xl font-black text-primary-foreground uppercase italic tracking-tighter">
                Analysis Complete
              </h2>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Neurobrutalism Trail / Matrix Elements */}
      <div className="absolute inset-0 z-5 pointer-events-none">
        {[...Array(10)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute bg-primary/10 border border-primary/20"
            initial={{
              width: Math.random() * 100 + 50,
              height: Math.random() * 20 + 5,
              x: Math.random() * 100 + '%',
              y: Math.random() * 100 + '%',
              opacity: 0,
            }}
            animate={{
              opacity: [0, 0.5, 0],
              x: [null, (Math.random() - 0.5) * 200 + 'px'],
            }}
            transition={{
              duration: Math.random() * 3 + 2,
              repeat: Number.POSITIVE_INFINITY,
              delay: Math.random() * 5,
            }}
          />
        ))}
      </div>
    </div>
  );
}
