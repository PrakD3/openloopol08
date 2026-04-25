export type InferenceMode = 'online' | 'offline';
export type AppMode = 'demo' | 'real';

export type VerdictType = 'real' | 'misleading' | 'ai-generated' | 'unverified';

export type AgentStatus = 'idle' | 'running' | 'done' | 'error';

export interface AgentFinding {
  agentId: string;
  agentName: string;
  status: AgentStatus;
  score: number | null;
  findings: string[];
  detail: string | null;
  duration?: number;
}

export interface AnalysisResult {
  jobId: string;
  verdict: VerdictType;
  credibilityScore: number;
  panicIndex: number;
  summary: string;
  sourceOrigin: string | null;
  originalDate: string | null;
  claimedLocation: string | null;
  actualLocation: string | null;
  latitude: number | null;
  longitude: number | null;
  keyFlags: string[];
  agents: AgentFinding[];
  videoUrl?: string;
  thumbnail?: string;
}

export interface DemoVideo {
  id: string;
  label: string;
  url: string;
  thumbnail: string;
  platform: 'youtube' | 'instagram' | 'twitter';
  precomputedResult: AnalysisResult;
}

export interface Incident {
  id: string;
  title: string;
  location: string;
  date: string;
  verdict: VerdictType;
  credibilityScore: number;
  panicIndex: number;
  videoCount: number;
  misinfoRate: number;
  summary: string;
  tags: string[];
}

export interface BulletinItem {
  id: string;
  title: string;
  content: string;
  verdict: VerdictType;
  source: string;
  timestamp: string;
  region: string;
}

export interface CommunityPost {
  id: string;
  author: string;
  avatar: string;
  content: string;
  videoUrl: string;
  verdict: VerdictType;
  votes: number;
  userVote: 'up' | 'down' | null;
  timestamp: string;
  replies: number;
}
