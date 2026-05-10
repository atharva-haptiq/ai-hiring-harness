import { NextRequest } from "next/server";

// Allow long-running SSE streams on Vercel / Next.js edge-compatible runtimes.
export const maxDuration = 300;

export async function POST(req: NextRequest) {
  const body = await req.json();

  const upstream = await fetch("http://localhost:8000/copilot/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  // Pipe the SSE stream straight through — do NOT buffer with res.json().
  // This lets the browser receive progress + token events in real time.
  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "Connection": "keep-alive",
      // Prevent Next.js / any middleware from compressing the stream,
      // which would buffer chunks and defeat the purpose of streaming.
      "Content-Encoding": "identity",
    },
  });
}
