import type { AnalysisResult, BulletinItem, CommunityPost, DemoVideo, Incident } from '@/types';

const DEMO_RESULT_REAL: AnalysisResult = {
  jobId: 'demo-real-001',
  verdict: 'real',
  credibilityScore: 91,
  panicIndex: 6,
  summary:
    'This video shows authentic footage of the 2023 Chennai flooding. The source is verified as BBC News India uploaded on 19 September 2023. GPS metadata and visual cues confirm the location.',
  sourceOrigin: 'https://www.youtube.com/watch?v=5xFbCOWgLWM',
  originalDate: '2023-09-19',
  disasterType: 'flood',
  claimedLocation: 'Chennai, Tamil Nadu, India',
  actualLocation: 'Chennai, Tamil Nadu, India',
  latitude: 13.0827,
  longitude: 80.2707,
  keyFlags: ['Verified source channel', 'EXIF metadata matches', 'No deepfake indicators'],
  videoUrl: 'https://www.youtube.com/watch?v=5xFbCOWgLWM',
  thumbnail: 'https://img.youtube.com/vi/5xFbCOWgLWM/maxresdefault.jpg',
  agents: [
    {
      agentId: 'deepfake-detector',
      agentName: 'DeepFake Detector',
      status: 'done',
      score: 3,
      findings: [
        'No facial manipulation detected',
        'Consistent lighting and shadow patterns',
        'Audio-visual sync verified',
      ],
      detail: 'CrossEfficientViT model confidence: 97% authentic. No GAN artifacts detected.',
      duration: 3200,
    },
    {
      agentId: 'source-hunter',
      agentName: 'Source Hunter',
      status: 'done',
      score: 92,
      findings: [
        'Earliest instance: BBC News India, 19 Sep 2023',
        'No prior uploads found with different context',
        'GPS embedded: 13.0827° N, 80.2707° E (Chennai)',
      ],
      detail:
        'Google Vision found 3 matching web pages, all from September 2023. TinEye: first seen 2023-09-19.',
      duration: 5100,
    },
    {
      agentId: 'context-analyser',
      agentName: 'Context Analyser',
      status: 'done',
      score: 89,
      findings: [
        'Audio: Tamil-language news commentary confirmed',
        'OCR: Tamil Nadu Government emergency text visible',
        'Architecture style matches Chennai',
        'Weather: historical rainfall data confirms flood event',
      ],
      detail:
        'Whisper transcription confirmed Tamil language. LLM vision analysis matches claimed location.',
      duration: 7000,
    },
  ],
};

const DEMO_RESULT_MISLEADING: AnalysisResult = {
  jobId: 'demo-misleading-001',
  verdict: 'misleading',
  credibilityScore: 24,
  panicIndex: 8,
  summary:
    'This video is real footage, but it is from the 2021 Uttarakhand glacier burst — NOT the 2023 Manipur floods as widely shared. The original source is 14 months older than the circulated claim.',
  sourceOrigin: 'https://www.youtube.com/watch?v=Zy1-WN2f0mE',
  originalDate: '2021-02-07',
  disasterType: 'flood',
  claimedLocation: 'Manipur, India (2023)',
  actualLocation: 'Chamoli, Uttarakhand, India (2021)',
  latitude: 30.415,
  longitude: 79.3333,
  keyFlags: [
    'Recirculated video — 14 months before claimed event',
    'Location mismatch confirmed by GPS and visual analysis',
    'Shared with false date context',
  ],
  videoUrl: 'https://www.youtube.com/watch?v=Zy1-WN2f0mE',
  thumbnail: 'https://img.youtube.com/vi/Zy1-WN2f0mE/maxresdefault.jpg',
  agents: [
    {
      agentId: 'deepfake-detector',
      agentName: 'DeepFake Detector',
      status: 'done',
      score: 5,
      findings: [
        'Video footage is authentic',
        'No manipulation detected',
        'Original camera metadata intact',
      ],
      detail: 'Video is real, but context is misleading. No deepfake indicators.',
      duration: 2800,
    },
    {
      agentId: 'source-hunter',
      agentName: 'Source Hunter',
      status: 'done',
      score: 18,
      findings: [
        'Earliest instance found: February 7, 2021',
        'Original upload predates claimed event by 14 months',
        'Found on 47 different pages with conflicting claims',
      ],
      detail:
        'TinEye: first seen 2021-02-07. Google Vision matched 47 web pages with 3 different location claims.',
      duration: 5400,
    },
    {
      agentId: 'context-analyser',
      agentName: 'Context Analyser',
      status: 'done',
      score: 12,
      findings: [
        'Location mismatch: Himalayas not Manipur valley',
        'Elevation and terrain inconsistent with claimed location',
        'Mountain geography confirms Uttarakhand',
      ],
      detail:
        'LLM vision analysis: mountain terrain, snow-capped peaks visible — inconsistent with Manipur geography.',
      duration: 6800,
    },
  ],
};

const DEMO_RESULT_AI_GENERATED: AnalysisResult = {
  jobId: 'demo-ai-001',
  verdict: 'ai-generated',
  credibilityScore: 8,
  panicIndex: 9,
  summary:
    'This video is AI-generated content falsely presented as footage of a tsunami. Multiple AI generation artifacts detected with 94% confidence. No matching real-world event found.',
  sourceOrigin: null,
  originalDate: null,
  disasterType: 'unknown',
  claimedLocation: 'Mumbai, India',
  actualLocation: null,
  latitude: 18.975,
  longitude: 72.8258,
  keyFlags: [
    'AI generation confidence: 94%',
    'GAN artifacts in water simulation',
    'No matching real event found',
    'Audio is synthetic',
  ],
  videoUrl: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
  thumbnail: 'https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg',
  agents: [
    {
      agentId: 'deepfake-detector',
      agentName: 'DeepFake Detector',
      status: 'done',
      score: 94,
      findings: [
        'GAN artifacts detected in 8/10 keyframes',
        'Unnatural water physics simulation',
        'Temporal inconsistency in crowd rendering',
        'Synthetic audio waveform detected',
      ],
      detail:
        'CrossEfficientViT: 94% AI-generated. UniversalFakeDetect: 97% fake. Consistent with diffusion model output.',
      duration: 3500,
    },
    {
      agentId: 'source-hunter',
      agentName: 'Source Hunter',
      status: 'done',
      score: 2,
      findings: [
        'No matching images found via reverse search',
        'No real-world event matches claimed date',
        'No EXIF metadata (stripped — common in AI-generated content)',
      ],
      detail: 'TinEye: 0 matches. Google Vision: no real-world matches. EXIF metadata absent.',
      duration: 4200,
    },
    {
      agentId: 'context-analyser',
      agentName: 'Context Analyser',
      status: 'done',
      score: 5,
      findings: [
        'Audio: synthetic voice-over, no ambient sound',
        'Architecture inconsistencies (non-existent buildings)',
        'No historical weather event matches',
        'OCR text has AI generation artifacts',
      ],
      detail:
        'Whisper detected synthesized speech patterns. LLM vision: buildings do not match Mumbai architecture.',
      duration: 6500,
    },
  ],
};

export const DEMO_VIDEOS: DemoVideo[] = [
  {
    id: 'demo-real-001',
    label: 'Real — Chennai Flooding (2023)',
    url: 'https://www.youtube.com/watch?v=5xFbCOWgLWM',
    thumbnail: 'https://img.youtube.com/vi/5xFbCOWgLWM/maxresdefault.jpg',
    platform: 'youtube',
    precomputedResult: DEMO_RESULT_REAL,
  },
  {
    id: 'demo-misleading-001',
    label: 'Misleading — Recirculated Flood Video',
    url: 'https://www.youtube.com/watch?v=Zy1-WN2f0mE',
    thumbnail: 'https://img.youtube.com/vi/Zy1-WN2f0mE/maxresdefault.jpg',
    platform: 'youtube',
    precomputedResult: DEMO_RESULT_MISLEADING,
  },
  {
    id: 'demo-ai-001',
    label: 'AI Generated — Fake Disaster Footage',
    url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    thumbnail: 'https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg',
    platform: 'youtube',
    precomputedResult: DEMO_RESULT_AI_GENERATED,
  },
];

export const MOCK_INCIDENTS: Incident[] = [
  {
    id: 'inc-001',
    title: 'Chennai Cyclone Michaung — Video Verification',
    location: 'Chennai, Tamil Nadu, India',
    date: '2023-12-04',
    verdict: 'misleading',
    credibilityScore: 31,
    panicIndex: 9,
    videoCount: 47,
    misinfoRate: 68,
    summary: '47 videos analysed. 68% were recycled from previous floods or AI-generated.',
    tags: ['cyclone', 'flooding', 'india', 'misinformation'],
  },
  {
    id: 'inc-002',
    title: 'Turkey-Syria Earthquake Aftermath',
    location: 'Kahramanmaraş, Turkey',
    date: '2023-02-06',
    verdict: 'misleading',
    credibilityScore: 42,
    panicIndex: 10,
    videoCount: 312,
    misinfoRate: 54,
    summary: '312 videos analysed during the crisis. 54% misrepresented scope or location.',
    tags: ['earthquake', 'turkey', 'syria', 'humanitarian'],
  },
  {
    id: 'inc-003',
    title: 'Morocco Earthquake Response',
    location: 'Al Haouz Province, Morocco',
    date: '2023-09-08',
    verdict: 'real',
    credibilityScore: 78,
    panicIndex: 7,
    videoCount: 89,
    misinfoRate: 22,
    summary: '89 videos. 78% verified authentic. Low misinformation rate for a major disaster.',
    tags: ['earthquake', 'morocco', 'africa'],
  },
];

export const MOCK_BULLETINS: BulletinItem[] = [
  {
    id: 'bull-001',
    title: 'CONFIRMED: Cyclone Remal Makes Landfall in Bangladesh',
    content:
      'Official meteorological data confirms Cyclone Remal made landfall near Mongla at 20:00 UTC. Authentic evacuation footage verified from 3 sources.',
    verdict: 'real',
    source: 'Bangladesh Meteorological Department',
    timestamp: '2024-05-26T20:00:00Z',
    region: 'Bangladesh',
  },
  {
    id: 'bull-002',
    title: 'DEBUNKED: "2024 Himalayan Tsunami" Video is AI-Generated',
    content:
      'Viral video claiming to show a tsunami in the Himalayas is confirmed AI-generated. 96% deepfake confidence. No such event occurred.',
    verdict: 'ai-generated',
    source: 'Vigilens Analysis #TL-2024-0891',
    timestamp: '2024-05-25T14:30:00Z',
    region: 'India',
  },
  {
    id: 'bull-003',
    title: 'UNVERIFIED: Flash Flood Videos Circulating from Assam',
    content:
      'Multiple videos claiming to show 2024 Assam floods are under analysis. Some appear to be from 2022 events. Verification ongoing.',
    verdict: 'unverified',
    source: 'Vigilens Community Report',
    timestamp: '2024-05-24T09:15:00Z',
    region: 'Assam, India',
  },
];

export const MOCK_COMMUNITY_POSTS: CommunityPost[] = [
  {
    id: 'post-001',
    author: 'disaster_watch_in',
    avatar: 'D',
    content:
      'Submitting this viral video — claims to be 2024 Kerala floods but architecture looks wrong',
    videoUrl: 'https://www.youtube.com/watch?v=5xFbCOWgLWM',
    verdict: 'misleading',
    votes: 47,
    userVote: null,
    timestamp: '2024-05-26T10:00:00Z',
    replies: 12,
  },
  {
    id: 'post-002',
    author: 'factcheck_asia',
    avatar: 'F',
    content:
      'Official NDRF footage confirmed authentic — I cross-checked with government press release',
    videoUrl: 'https://www.youtube.com/watch?v=Zy1-WN2f0mE',
    verdict: 'real',
    votes: 103,
    userVote: null,
    timestamp: '2024-05-26T08:30:00Z',
    replies: 8,
  },
];
