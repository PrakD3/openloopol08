import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Cpu, Eye, GitMerge, Globe, Server, Zap } from 'lucide-react';

export default function HowItWorksPage() {
  const pipeline = [
    {
      step: 1,
      icon: Cpu,
      name: 'Preprocess',
      desc: 'FFmpeg extracts keyframes every 2 seconds and audio track from the video',
      tech: ['FFmpeg', 'OpenCV'],
    },
    {
      step: 2,
      icon: Zap,
      name: 'DeepFake Detector',
      desc: 'Analyses keyframes using Vertex AI and Groq Vision for synthetic artifacts and AI generation signatures',
      tech: ['Vertex AI', 'Groq Vision'],
    },
    {
      step: 3,
      icon: Eye,
      name: 'Source Hunter',
      desc: 'Perceptual hashing + Google Vision reverse image search finds the earliest known upload and EXIF metadata',
      tech: ['pHash', 'Google Vision', 'TinEye', 'ExifTool'],
    },
    {
      step: 4,
      icon: Globe,
      name: 'Context Analyser',
      desc: 'Whisper transcribes audio, EasyOCR reads on-screen text, vision LLM verifies location and temporal context',
      tech: ['Whisper', 'EasyOCR', 'Groq', 'Gemini'],
    },
    {
      step: 5,
      icon: GitMerge,
      name: 'Orchestrator',
      desc: 'LLM synthesises all agent findings into a final public verdict with credibility score and panic index',
      tech: ['LangGraph', 'Groq', 'LangSmith'],
    },
  ];

  return (
    <div className="min-h-screen py-16 px-4 bg-background bk-noise">
      <div className="mx-auto max-w-5xl">
        <div className="text-center mb-16 space-y-4">
          <div className="inline-block bg-primary border-4 border-foreground p-4 bk-shadow-md -rotate-1">
            <h1 className="text-5xl md:text-7xl font-black uppercase tracking-tighter leading-none">
              How Vigilens Works
            </h1>
          </div>
          <p className="text-xl font-black text-muted-foreground uppercase tracking-widest">
            A three-stage AI pipeline for real-time verification
          </p>
        </div>

        {/* Architecture Diagram */}
        <Card className="mb-12 border-4 border-foreground shadow-bk bg-secondary/10">
          <CardHeader className="border-b-4 border-foreground bg-secondary/20">
            <CardTitle className="flex items-center gap-3 font-black uppercase tracking-tight">
              <Server className="h-6 w-6" />
              Architecture Overview
            </CardTitle>
          </CardHeader>
          <CardContent className="p-8">
            <pre className="text-sm font-black font-mono text-foreground overflow-x-auto whitespace-pre p-6 bg-background border-4 border-foreground bk-shadow-sm">
              {`VIGILENS-OS-ALPHA
=================
Next.js Frontend [UI-LAYER]
      │  POST /api/analyze
      ▼
FastAPI Backend [CORE-LOGIC]
      │  LangGraph StateGraph
      ▼
   [PREPROCESS]
   ┌─────────────────────────────────┐
   │  Extract Keyframes + Audio      │
   └─────────────────────────────────┘
      │
      ├──────────────────┬──────────────────┐
      │                  │                  │
      ▼                  ▼                  ▼
[DEEPFAKE DETECTOR] [SOURCE HUNTER]    [CONTEXT ANALYSER]
 Vertex AI / Groq   Google Vision      Whisper + EasyOCR
 Vision LLM         TinEye / pHash     Vision LLM
      │                  │                  │
      └──────────────────┼──────────────────┘
                        │
                        ▼
                [ORCHESTRATOR]
                Groq / Gemini LLM
                LangSmith Tracing
                        │
                        ▼
                FINAL VERDICT JSON`}
            </pre>
          </CardContent>
        </Card>

        {/* Pipeline Steps */}
        <div className="space-y-6">
          <h3 className="text-2xl font-black uppercase tracking-tighter italic border-b-8 border-foreground inline-block mb-4">
            Pipeline Protocol
          </h3>
          {pipeline.map((step) => (
            <Card key={step.step} className="border-4 shadow-bk bk-hover-scale bg-background">
              <CardHeader className="pb-4">
                <div className="flex items-center gap-6">
                  <div className="h-14 w-14 border-4 border-foreground bg-accent text-foreground flex items-center justify-center text-2xl font-black shrink-0 bk-shadow-sm rotate-3">
                    {step.step}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <step.icon className="h-6 w-6 text-foreground" />
                      <CardTitle className="text-2xl font-black uppercase tracking-tight">
                        {step.name}
                      </CardTitle>
                    </div>
                    <p className="text-base font-bold text-muted-foreground mt-1">{step.desc}</p>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-0 pb-6 pl-[88px]">
                <div className="flex flex-wrap gap-2">
                  {step.tech.map((t) => (
                    <Badge
                      key={t}
                      variant="secondary"
                      className="border-2 text-[10px] font-black uppercase tracking-widest px-3 py-1"
                    >
                      {t}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Mode Guide */}
        <div className="mt-16 grid md:grid-cols-2 gap-8">
          <Card className="border-4 border-foreground shadow-bk bg-accent/20">
            <CardHeader className="border-b-4 border-foreground">
              <CardTitle className="text-2xl font-black uppercase tracking-tight flex items-center gap-3">
                <Globe className="h-6 w-6" /> Online Mode
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-3">
              {[
                'LLM: Groq API (llama-3.3-70b)',
                'DeepFake: Vertex AI / Groq Vision',
                'Transcription: OpenAI Whisper API',
                'Reverse Search: Google Vision + TinEye',
                'Requires API keys — see .env.example',
              ].map((item, i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 font-black text-sm uppercase tracking-tight"
                >
                  <div className="h-2 w-2 bg-foreground" /> {item}
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
