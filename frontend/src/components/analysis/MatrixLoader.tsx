'use client';

import { DEMO_VIDEOS } from '@/lib/demoData';
import { cn } from '@/lib/utils';
import { AnimatePresence, motion } from 'framer-motion';
import { useEffect, useMemo, useState } from 'react';

interface MatrixLoaderProps {
  videoUrl: string;
  isComplete: boolean;
  onAnimationComplete?: () => void;
}

const GRID_SIZE = 15;

export function MatrixLoader({ videoUrl, isComplete, onAnimationComplete }: MatrixLoaderProps) {
  const [thumbnail, setThumbnail] = useState<string | null>(null);
  const [isPortrait, setIsPortrait] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  useEffect(() => {
    const fetchMetadata = async () => {
      // First check demo data
      const demo = DEMO_VIDEOS.find((v) => v.url === videoUrl);
      if (demo) {
        setThumbnail(demo.thumbnail);
        return;
      }

      // Then try YouTube regex for quick local resolution
      const ytMatch = videoUrl.match(
        /(?:https?:\/\/)?(?:www\.)?(?:youtube\.com|youtu\.be)\/(?:watch\?v=)?(?:embed\/)?(?:v\/)?(?:shorts\/)?([^?&"'>]+)/
      );
      if (ytMatch?.[1]) {
        setThumbnail(`https://img.youtube.com/vi/${ytMatch[1]}/hqdefault.jpg`);
        return;
      }

      // Finally, call our metadata API for other sites (Reddit, X, etc.)
      try {
        const response = await fetch(`/api/metadata?url=${encodeURIComponent(videoUrl)}`);
        if (response.ok) {
          const data = await response.json();
          if (data.thumbnail) {
            setThumbnail(data.thumbnail);
          } else {
            setThumbnail('/images/forensic-placeholder.png');
          }
        } else {
          setThumbnail('/images/forensic-placeholder.png');
        }
      } catch (_err) {
        setThumbnail('/images/forensic-placeholder.png');
      }
    };

    if (videoUrl) {
      fetchMetadata();
    }
  }, [videoUrl]);

  const handleImageLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    const { naturalWidth, naturalHeight } = e.currentTarget;
    setIsPortrait(naturalHeight > naturalWidth);
  };

  // Staggered grid origin
  const gridOrigin = useMemo(
    () => [Math.floor(Math.random() * GRID_SIZE), Math.floor(Math.random() * GRID_SIZE)],
    []
  );

  const getDistance = (row: number, col: number) => {
    return (
      Math.sqrt((row - gridOrigin[0]) ** 2 + (col - gridOrigin[1]) ** 2) /
      (GRID_SIZE * Math.sqrt(2))
    );
  };

  return (
    <div className="relative w-full h-[600px] bg-black overflow-hidden border-4 border-foreground bk-shadow-lg flex items-center justify-center">
      {/* Background Matrix Grid */}
      <div className="absolute inset-0 z-0 opacity-10">
        <div
          className="w-full h-full"
          style={{
            backgroundImage:
              'linear-gradient(to right, #333 1px, transparent 1px), linear-gradient(to bottom, #333 1px, transparent 1px)',
            backgroundSize: '30px 30px',
          }}
        />
      </div>

      {/* Dynamic Grid Box Overlay */}
      <motion.div
        className="absolute inset-0 z-10 border-2 border-primary/20"
        animate={{
          backgroundPosition: ['0% 0%', '100% 100%'],
        }}
        transition={{
          duration: 30,
          repeat: Number.POSITIVE_INFINITY,
          ease: 'linear',
        }}
        style={{
          backgroundImage:
            'radial-gradient(circle at center, transparent 0%, rgba(0,0,0,0.6) 100%)',
        }}
      />

      {/* Main Content Area */}
      <div className="relative z-20 w-full h-full flex items-center justify-center p-8">
        <AnimatePresence mode="wait">
          {!isComplete ? (
            <motion.div
              key="loader-content"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{
                scale: 1.5,
                opacity: 0,
                filter: 'blur(20px)',
                transition: { duration: 1, ease: [0.16, 1, 0.3, 1] },
              }}
              className="relative w-full h-full flex flex-col items-center justify-center"
              onMouseEnter={() => setIsHovered(true)}
              onMouseLeave={() => setIsHovered(false)}
            >
              {thumbnail ? (
                <div
                  className={cn(
                    'relative border-4 border-foreground bk-shadow-xl overflow-hidden bg-muted group transition-all duration-500',
                    isPortrait ? 'h-[90%] aspect-[9/16]' : 'w-full h-[80%]'
                  )}
                >
                  <img
                    src={thumbnail}
                    alt="Source Preview"
                    onLoad={handleImageLoad}
                    className={cn(
                      'w-full h-full object-cover transition-transform duration-1000',
                      !isPortrait && 'scale-105',
                      isHovered && 'scale-110 blur-[2px]'
                    )}
                  />

                  {/* Interactive Staggered Grid Overlay */}
                  <div
                    className="absolute inset-0 grid gap-[1.5px] opacity-90 z-20"
                    style={{
                      gridTemplateColumns: `repeat(${GRID_SIZE}, 1fr)`,
                      gridTemplateRows: `repeat(${GRID_SIZE}, 1fr)`,
                    }}
                  >
                    {[...Array(GRID_SIZE ** 2)].map((_, idx) => {
                      const row = Math.floor(idx / GRID_SIZE);
                      const col = idx % GRID_SIZE;
                      const dist = getDistance(row, col);

                      return (
                        <motion.div
                          // biome-ignore lint/suspicious/noArrayIndexKey: grid index is stable
                          key={idx}
                          className="bg-primary/50 border-[1px] border-primary/30 backdrop-blur-[2px] cursor-none"
                          initial={{ opacity: 0, scale: 0 }}
                          animate={
                            !isHovered
                              ? {
                                  opacity: [0.3, 0.7, 0.3],
                                  scale: [0.95, 1, 0.95],
                                }
                              : {
                                  opacity: 0.15,
                                  scale: 0.98,
                                }
                          }
                          whileHover={{
                            scale: 1.5,
                            backgroundColor: 'rgba(var(--primary), 0.9)',
                            borderColor: 'rgba(var(--primary), 1)',
                            boxShadow: '0 0 15px rgba(var(--primary), 0.8)',
                            zIndex: 100,
                            transition: { duration: 0.1 },
                          }}
                          transition={{
                            duration: 2,
                            repeat: Number.POSITIVE_INFINITY,
                            delay: dist * 1.5,
                            ease: 'easeInOut',
                          }}
                          style={{
                            mixBlendMode: 'screen',
                          }}
                        />
                      );
                    })}
                  </div>

                  {/* Platform Badge */}
                  <div className="absolute top-6 left-6 z-40 bg-foreground text-background px-4 py-2 text-xs font-black uppercase tracking-[0.2em] border-2 border-primary shadow-[0_0_20px_rgba(var(--primary),0.6)]">
                    {videoUrl.includes('youtube.com') || videoUrl.includes('youtu.be')
                      ? 'Source: YouTube'
                      : videoUrl.includes('reddit.com')
                        ? 'Source: Reddit'
                        : videoUrl.includes('twitter.com') || videoUrl.includes('x.com')
                          ? 'Source: X / Twitter'
                          : 'Source: External Link'}
                  </div>

                  {/* Matrix Escape Elements (Flinging out on Complete) */}
                  <div className="absolute inset-0 pointer-events-none z-50">
                    {[...Array(20)].map((_, i) => (
                      <motion.div
                        // biome-ignore lint/suspicious/noArrayIndexKey: static list
                        key={`particle-${i}`}
                        className="absolute w-2 h-2 bg-primary"
                        initial={{ opacity: 0 }}
                        exit={{
                          opacity: [0, 1, 0],
                          x: (Math.random() - 0.5) * 1000,
                          y: (Math.random() - 0.5) * 1000,
                          scale: [1, 2, 0],
                          transition: { duration: 0.8, ease: 'easeOut' },
                        }}
                        style={{
                          left: `${Math.random() * 100}%`,
                          top: `${Math.random() * 100}%`,
                        }}
                      />
                    ))}
                  </div>

                  {/* Glitch Overlay */}
                  <div className="absolute inset-0 pointer-events-none mix-blend-overlay opacity-20 bk-diagonal-lines" />
                </div>
              ) : (
                <div className="w-64 h-64 border-4 border-foreground flex items-center justify-center bg-background bk-shadow-lg animate-pulse">
                  <div className="w-16 h-16 border-4 border-primary border-t-transparent animate-spin" />
                </div>
              )}

              <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-center space-y-3 bg-background/95 p-6 border-4 border-foreground bk-shadow-xl min-w-[400px] z-50">
                <p className="text-4xl font-black uppercase tracking-tighter italic text-foreground leading-none">
                  Running AI pipeline
                </p>
                <div className="flex items-center justify-center gap-6">
                  <div className="h-1.5 w-16 bg-primary" />
                  <p className="text-xs font-bold text-muted-foreground uppercase tracking-[0.5em]">
                    Forensic Sweep In Progress
                  </p>
                  <div className="h-1.5 w-16 bg-primary" />
                </div>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="complete-flash"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              onAnimationComplete={onAnimationComplete}
              className="absolute inset-0 bg-primary z-[100] flex flex-col items-center justify-center"
            >
              <motion.h2
                initial={{ letterSpacing: '0.5em' }}
                animate={{ letterSpacing: '-0.05em' }}
                transition={{ duration: 0.5, ease: 'easeOut' }}
                className="text-9xl font-black text-primary-foreground uppercase italic tracking-tighter"
              >
                SUCCESS
              </motion.h2>
              <p className="text-xl font-black text-primary-foreground/80 uppercase tracking-[1em] mt-4">
                Analysis Complete
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Ambient Neurobrutalism Trail */}
      <div className="absolute inset-0 z-5 pointer-events-none">
        {[...Array(12)].map((_, i) => (
          <motion.div
            // biome-ignore lint/suspicious/noArrayIndexKey: static list
            key={`glitch-${i}`}
            className="absolute bg-primary/5 border border-primary/10"
            initial={{
              width: Math.random() * 150 + 50,
              height: Math.random() * 30 + 10,
              x: `${Math.random() * 100}%`,
              y: `${Math.random() * 100}%`,
              opacity: 0,
            }}
            animate={{
              opacity: [0, 0.3, 0],
              x: [null, `${(Math.random() - 0.5) * 300}px`],
            }}
            transition={{
              duration: Math.random() * 4 + 3,
              repeat: Number.POSITIVE_INFINITY,
              delay: Math.random() * 5,
            }}
          />
        ))}
      </div>
    </div>
  );
}
