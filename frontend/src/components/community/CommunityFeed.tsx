'use client';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { MOCK_COMMUNITY_POSTS } from '@/lib/demoData';
import { cn } from '@/lib/utils';
import type { CommunityPost } from '@/types';
import { MessageCircle, ThumbsDown, ThumbsUp } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

export function CommunityFeed() {
  const { t } = useTranslation();
  const [posts, setPosts] = useState<CommunityPost[]>(MOCK_COMMUNITY_POSTS);

  const handleVote = (postId: string, vote: 'up' | 'down') => {
    setPosts((prev) =>
      prev.map((p) => {
        if (p.id !== postId) return p;
        const wasVoted = p.userVote === vote;
        return {
          ...p,
          votes: wasVoted ? p.votes - 1 : p.userVote ? p.votes : p.votes + 1,
          userVote: wasVoted ? null : vote,
        };
      })
    );
  };

  return (
    <div className="space-y-6">
      <h3 className="font-black text-xs text-foreground uppercase tracking-[0.2em] bg-clash-3 inline-block px-3 py-1 border-3 border-foreground bk-shadow-sm mb-2">
        Community Reports
      </h3>
      {posts.map((post) => (
        <Card key={post.id} className="border-4 shadow-bk animate-fade-in-up">
          <CardContent className="p-6">
            <div className="flex items-start gap-4">
              <div className="h-12 w-12 border-3 border-foreground bg-primary text-foreground flex items-center justify-center text-xl font-black shrink-0 bk-shadow-sm rotate-3 group-hover:rotate-0 transition-transform">
                {post.avatar}
              </div>
              <div className="flex-1 min-w-0 space-y-3">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="text-sm font-black uppercase tracking-tight bg-muted px-2 py-0.5 border-2 border-foreground">
                    @{post.author}
                  </span>
                  <Badge
                    variant={post.verdict as 'real' | 'misleading' | 'unverified'}
                    className="border-2"
                  >
                    {t(`verdict.${post.verdict}`).toUpperCase()}
                  </Badge>
                </div>
                <p className="text-base font-bold leading-tight border-l-4 border-foreground/20 pl-4">
                  {post.content}
                </p>
                <div className="flex items-center gap-4">
                  <div className="flex border-3 border-foreground bk-shadow-sm bg-background">
                    <Button
                      variant="ghost"
                      size="sm"
                      className={cn(
                        'h-10 px-4 gap-2 font-black rounded-none border-r-3 border-foreground hover:bg-secondary/20',
                        post.userVote === 'up' && 'bg-secondary text-white'
                      )}
                      onClick={() => handleVote(post.id, 'up')}
                    >
                      <ThumbsUp className="h-4 w-4" />
                      <span className="text-sm">{post.votes}</span>
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className={cn(
                        'h-10 px-4 rounded-none hover:bg-destructive/20',
                        post.userVote === 'down' && 'bg-destructive/20'
                      )}
                      onClick={() => handleVote(post.id, 'down')}
                    >
                      <ThumbsDown className="h-4 w-4" />
                    </Button>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-10 px-4 gap-2 font-black border-3"
                  >
                    <MessageCircle className="h-4 w-4" />
                    <span className="text-sm">{post.replies} REPLIES</span>
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
