import { config } from '@/lib/config';
import { DEMO_VIDEOS } from '@/lib/demoData';
import { type NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = config.backendUrl;
const POLL_INTERVAL_MS = 2000;
const MAX_POLL_RETRIES = 200; // 400s total

export async function POST(req: NextRequest) {
  const body = (await req.json()) as { videoUrl: string };
  const { videoUrl } = body;

  // ── Demo mode ──────────────────────────────────────────────────────────────
  if (config.isDemo) {
    const demo = DEMO_VIDEOS.find((v) => v.url === videoUrl);
    if (!demo) {
      return NextResponse.json(
        {
          error: 'URL not available in demo dataset. Use a demo video or switch APP_MODE to real.',
        },
        { status: 400 }
      );
    }
    await new Promise((r) => setTimeout(r, 2000));
    return NextResponse.json(demo.precomputedResult);
  }

  // ── Real mode ──────────────────────────────────────────────────────────────
  try {
    // Step 1: POST /analyze to kick off the background job
    const analyzeUrl = `${BACKEND_URL}/analyze`;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
      controller.abort();
    }, 60_000);

    let initialResponse: Response;
    try {
      initialResponse = await fetch(analyzeUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_url: videoUrl }),
        signal: controller.signal,
      });
    } finally {
      clearTimeout(timeoutId);
    }

    if (!initialResponse.ok) {
      let errorBody = '<could not read body>';
      try {
        errorBody = await initialResponse.text();
      } catch (_) {}
      return NextResponse.json(
        { error: `Backend returned ${initialResponse.status}: ${errorBody}` },
        { status: 502 }
      );
    }

    const startPayload = await initialResponse.json();
    const { job_id } = startPayload as { job_id: string; status: string };

    if (!job_id) {
      return NextResponse.json({ error: 'Backend did not return a job_id' }, { status: 502 });
    }

    // Step 2: Poll /status/:job_id until completed, failed, or timeout
    for (let i = 0; i < MAX_POLL_RETRIES; i++) {
      await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));

      const statusUrl = `${BACKEND_URL}/status/${job_id}`;
      let statusResponse: Response;

      try {
        statusResponse = await fetch(statusUrl);
      } catch (_fetchErr) {
        continue;
      }

      if (!statusResponse.ok) {
        let _errBody = '<unreadable>';
        try {
          _errBody = await statusResponse.text();
        } catch (_) {}
        continue;
      }

      let job: Record<string, unknown>;
      try {
        job = await statusResponse.json();
      } catch (_parseErr) {
        continue;
      }

      const jobStatus = job.status as string | undefined;
      const _jobStage = (job.stage as string | undefined) ?? '';

      if (jobStatus === 'completed') {
        const result = job.result;
        if (result == null) {
          return NextResponse.json(
            { error: 'Analysis completed but result was empty — please retry' },
            { status: 502 }
          );
        }

        return NextResponse.json(result);
      }

      if (jobStatus === 'failed') {
        const jobError = job.error ?? 'Unknown error';
        return NextResponse.json({ error: String(jobError) }, { status: 500 });
      }

      // Still processing — log a heartbeat every 10 polls to reduce noise
      if ((i + 1) % 10 === 0) {
        // Heartbeat log placeholder
      }
    }

    // Exhausted retries
    const totalWaitedSecs = (MAX_POLL_RETRIES * POLL_INTERVAL_MS) / 1000;
    return NextResponse.json(
      {
        error: `Analysis timed out after ${totalWaitedSecs}s. The job (${job_id}) is still running on the backend — submitting the same URL again will reuse the existing job instead of starting a new one.`,
        job_id,
      },
      { status: 504 }
    );
  } catch (err: unknown) {
    if (err instanceof Error && err.name === 'AbortError') {
      return NextResponse.json(
        {
          error: 'Backend took too long to acknowledge the analysis request (>60s)',
        },
        { status: 504 }
      );
    }
    return NextResponse.json(
      {
        error: `Backend unreachable at ${BACKEND_URL}. Is it running? Detail: ${err instanceof Error ? err.message : String(err)}`,
      },
      { status: 503 }
    );
  }
}
