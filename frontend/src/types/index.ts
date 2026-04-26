export type InferenceMode = 'online' | 'offline';
export type AppMode = 'demo' | 'real';

export type VerdictType = 'real' | 'misleading' | 'ai-generated' | 'unverified';

export type AgentStatus = 'idle' | 'running' | 'done' | 'error';

export interface ModelScore {
  modelName: string;
  authenticPct: number;
  fakePct: number;
  confidence: number;
}

export interface AgentFinding {
  agentId: string;
  agentName: string;
  status: AgentStatus;
  score: number | null;
  findings: string[];
  detail: string | null;
  duration?: number;
  constraintsSatisfied?: number;
  totalConstraints?: number;
  constraintDetails?: Record<string, boolean>;
  modelScores?: ModelScore[]; // deepfake agent only
}

export interface SOSRegion {
  lat: number;
  lng: number;
  radiusKm: number;
  centerName: string;
  disasterType: string;
  panicIndex: number;
  color: string;
  sosActive: boolean;
}

export interface AnalysisResult {
  jobId: string;
  verdict: VerdictType;
  credibilityScore: number;
  panicIndex: number;
  summary: string;
  disasterType: string;
  sourceOrigin: string | null;
  originalDate: string | null;
  claimedLocation: string | null;
  actualLocation: string | null;
  latitude?: number | null;
  longitude?: number | null;
  keyFlags: string[];
  agents: AgentFinding[];
  sosRegion?: SOSRegion | null;
  videoUrl?: string;
  thumbnail?: string;
  uploaderIntelligence?: UploaderIntelligence | null;
  reverseSearch?: ReverseSearchResult | null;
  commentIntelligence?: CommentIntelligence | null;
  platformMetadata?: Record<string, unknown> | null;
  redditMetadata?: Record<string, unknown> | null;
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

export interface UploaderIntelligence {
  trustScore: number;
  uploaderSummary: string;
  accountAgeSignal: string;
  redFlags: string[];
  trustSignals: string[];
  temporalNote: string | null;
  platformNotes: string | null;
}

export interface ReverseSearchResult {
  status: string;
  priorAppearancesCount: number;
  temporalDisplacementRisk: string;
  bestGuessLabels: string[];
  matchingPages: Array<{ url: string; title: string }>;
  earliestKnownPage: { url: string; title: string } | null;
}

export interface CommentIntelligence {
  communityVerdict: string;
  consensusSummary: string;
  originalSourceClaims: string[];
  locationCorrections: string[];
  dateCorrections: string[];
  debunkSignals: string[];
  confirmSignals: string[];
  notableComment: string | null;
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
