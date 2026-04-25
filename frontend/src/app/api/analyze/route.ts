import { NextRequest, NextResponse } from "next/server";
import { config } from "@/lib/config";
import { DEMO_VIDEOS } from "@/lib/demoData";

const BACKEND_URL = "http://127.0.0.1:8888";
const POLL_INTERVAL_MS = 2000;
const MAX_POLL_RETRIES = 120; // 240s total

function ts(): string {
  return new Date().toISOString().replace("T", " ").slice(0, -1);
}

export async function POST(req: NextRequest) {
  console.log(`\n[${ts()}] !!! [PROXY] API ROUTE HIT !!!`);

  const body = (await req.json()) as { videoUrl: string };
  const { videoUrl } = body;

  console.log(`[${ts()}] [PROXY] Analyze Request : ${videoUrl}`);
  console.log(`[${ts()}] [PROXY] Target Backend  : ${BACKEND_URL}/analyze`);
  console.log(`[${ts()}] [PROXY] Demo mode       : ${config.isDemo}`);

  // ── Demo mode ──────────────────────────────────────────────────────────────
  if (config.isDemo) {
    console.log(
      `[${ts()}] [PROXY] Running in DEMO mode — skipping real backend`,
    );
    const demo = DEMO_VIDEOS.find((v) => v.url === videoUrl);
    if (!demo) {
      console.warn(`[${ts()}] [PROXY] DEMO: URL not found in demo dataset`);
      return NextResponse.json(
        {
          error:
            "URL not available in demo dataset. Use a demo video or switch APP_MODE to real.",
        },
        { status: 400 },
      );
    }
    console.log(
      `[${ts()}] [PROXY] DEMO: Found precomputed result — returning after 2s delay`,
    );
    await new Promise((r) => setTimeout(r, 2000));
    return NextResponse.json(demo.precomputedResult);
  }

  // ── Real mode ──────────────────────────────────────────────────────────────
  try {
    // Step 1: POST /analyze to kick off the background job
    const analyzeUrl = `${BACKEND_URL}/analyze`;
    console.log(`[${ts()}] [PROXY] POSTing to ${analyzeUrl} ...`);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
      console.error(
        `[${ts()}] [PROXY] AbortController fired — backend took >60s to acknowledge the job`,
      );
      controller.abort();
    }, 60_000);

    let initialResponse: Response;
    try {
      initialResponse = await fetch(analyzeUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_url: videoUrl }),
        signal: controller.signal,
      });
    } finally {
      clearTimeout(timeoutId);
    }

    console.log(
      `[${ts()}] [PROXY] Backend responded — HTTP ${initialResponse.status} ${initialResponse.statusText}`,
    );

    if (!initialResponse.ok) {
      let errorBody = "<could not read body>";
      try {
        errorBody = await initialResponse.text();
      } catch (_) {}
      console.error(
        `[${ts()}] [PROXY] Backend returned error ${initialResponse.status}. Body: ${errorBody}`,
      );
      return NextResponse.json(
        { error: `Backend returned ${initialResponse.status}: ${errorBody}` },
        { status: 502 },
      );
    }

    const startPayload = await initialResponse.json();
    const { job_id } = startPayload as { job_id: string; status: string };

    if (!job_id) {
      console.error(
        `[${ts()}] [PROXY] Backend did not return a job_id. Payload: ${JSON.stringify(startPayload)}`,
      );
      return NextResponse.json(
        { error: "Backend did not return a job_id" },
        { status: 502 },
      );
    }

    console.log(
      `[${ts()}] [PROXY] Job started: ${job_id}. Starting polling (max ${MAX_POLL_RETRIES} × ${POLL_INTERVAL_MS}ms) ...`,
    );

    // Step 2: Poll /status/:job_id until completed, failed, or timeout
    for (let i = 0; i < MAX_POLL_RETRIES; i++) {
      await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));

      const statusUrl = `${BACKEND_URL}/status/${job_id}`;
      let statusResponse: Response;

      try {
        statusResponse = await fetch(statusUrl);
      } catch (fetchErr) {
        console.warn(
          `[${ts()}] [PROXY] Poll ${i + 1}/${MAX_POLL_RETRIES} — fetch error (will retry): ${fetchErr}`,
        );
        continue;
      }

      if (!statusResponse.ok) {
        let errBody = "<unreadable>";
        try {
          errBody = await statusResponse.text();
        } catch (_) {}
        console.warn(
          `[${ts()}] [PROXY] Poll ${i + 1}/${MAX_POLL_RETRIES} — HTTP ${statusResponse.status} from status endpoint. Body: ${errBody}`,
        );
        continue;
      }

      let job: Record<string, unknown>;
      try {
        job = await statusResponse.json();
      } catch (parseErr) {
        console.warn(
          `[${ts()}] [PROXY] Poll ${i + 1}/${MAX_POLL_RETRIES} — JSON parse error: ${parseErr}`,
        );
        continue;
      }

      const jobStatus = job.status as string | undefined;
      const jobProgress = job.progress ?? "?";
      const jobStage = (job.stage as string | undefined) ?? "";

      console.log(
        `[${ts()}] [PROXY] Poll ${i + 1}/${MAX_POLL_RETRIES} — job=${job_id.slice(0, 8)} status=${JSON.stringify(jobStatus)} progress=${typeof jobProgress === "number" ? `${Math.round((jobProgress as number) * 100)}%` : jobProgress} stage=${JSON.stringify(jobStage)}`,
      );

      if (jobStatus === "completed") {
        const result = job.result;
        if (result == null) {
          console.error(
            `[${ts()}] [PROXY] Job ${job_id.slice(0, 8)} completed but result is null/undefined — this is a backend bug`,
          );
          return NextResponse.json(
            { error: "Analysis completed but result was empty — please retry" },
            { status: 502 },
          );
        }

        const resultObj = result as Record<string, unknown>;
        console.log(
          `[${ts()}] [PROXY] Job ${job_id.slice(0, 8)} COMPLETED ✓ — ` +
            `verdict=${resultObj.verdict ?? "?"}  ` +
            `credibility=${resultObj.credibilityScore ?? resultObj.credibility_score ?? "?"}  ` +
            `panic=${resultObj.panicIndex ?? resultObj.panic_index ?? "?"}  ` +
            `flags=${JSON.stringify(resultObj.keyFlags ?? resultObj.key_flags ?? [])}`,
        );
          console.log(
            `[${ts()}] [PROXY] Agent summary - ${JSON.stringify(
              Array.isArray(resultObj.agents)
                ? resultObj.agents.map((agent) => {
                    const agentObj = agent as Record<string, unknown>;
                    return {
                      id: agentObj.agentId ?? agentObj.agent_id,
                      status: agentObj.status,
                      score: agentObj.score,
                    };
                  })
                : [],
            )}`,
          );
          console.log(
            `[${ts()}] [PROXY] Returning completed result to client (poll #${i + 1}, ~${((i + 1) * POLL_INTERVAL_MS) / 1000}s elapsed)`,
          );

        return NextResponse.json(result);
      }

      if (jobStatus === "failed") {
        const jobError = job.error ?? "Unknown error";
        console.error(
          `[${ts()}] [PROXY] Job ${job_id.slice(0, 8)} FAILED on backend. error=${JSON.stringify(jobError)}`,
        );
        return NextResponse.json({ error: String(jobError) }, { status: 500 });
      }

      // Still processing — log a heartbeat every 10 polls to reduce noise
      if ((i + 1) % 10 === 0) {
        const secsElapsed = ((i + 1) * POLL_INTERVAL_MS) / 1000;
        const secsRemaining =
          ((MAX_POLL_RETRIES - i - 1) * POLL_INTERVAL_MS) / 1000;
        const progressPct =
          typeof jobProgress === "number"
            ? `${Math.round((jobProgress as number) * 100)}%`
            : "?%";
        console.log(
          `[${ts()}] [PROXY] ... still waiting — ${secsElapsed}s elapsed, ${secsRemaining}s remaining — progress=${progressPct} stage=${JSON.stringify(jobStage)}`,
        );
      }
    }

    // Exhausted retries
    const totalWaitedSecs = (MAX_POLL_RETRIES * POLL_INTERVAL_MS) / 1000;
    console.error(
      `[${ts()}] [PROXY] TIMEOUT — job ${job_id.slice(0, 8)} did not complete within ` +
        `${MAX_POLL_RETRIES} polls (${totalWaitedSecs}s). ` +
        `The backend job may still be running; check backend logs for job_id=${job_id}`,
    );
    return NextResponse.json(
      {
        error:
          `Analysis timed out after ${totalWaitedSecs}s. ` +
          `The job (${job_id}) is still running on the backend — ` +
          `submitting the same URL again will reuse the existing job instead of starting a new one.`,
        job_id,
      },
      { status: 504 },
    );
  } catch (err: unknown) {
    if (err instanceof Error && err.name === "AbortError") {
      console.error(
        `[${ts()}] [PROXY] ABORT: Backend at ${BACKEND_URL} took >60s to start the job. ` +
          `Is the backend running and healthy?`,
      );
      return NextResponse.json(
        {
          error:
            "Backend took too long to acknowledge the analysis request (>60s)",
        },
        { status: 504 },
      );
    }

    console.error(`[${ts()}] [PROXY] CRITICAL UNHANDLED ERROR:`);
    console.error(err);
    return NextResponse.json(
      {
        error: `Backend unreachable at ${BACKEND_URL}. Is it running? Detail: ${err instanceof Error ? err.message : String(err)}`,
      },
      { status: 503 },
    );
  }
}
