"use client";

import { useState, useRef, useEffect } from "react";
import { Onest } from "next/font/google";
import Link from "next/link";
import { ArrowLeft, Send } from "lucide-react";

const onest = Onest({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700", "800"],
  variable: "--font-onest",
});

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function CopilotPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Hi! I'm your Hiring Copilot. Ask me anything about your candidates, job descriptions, or hiring decisions.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSend(e?: React.FormEvent) {
    e?.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    const userMessage: Message = { role: "user", content: text };
    // Add only the user message now; the assistant bubble is inserted on the
    // first token event so the loading dots are the sole waiting indicator.
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("/api/copilot/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });

      if (!res.ok || !res.body) {
        const err = await res.text();
        throw new Error(err || `Server error: ${res.status}`);
      }

      // Read the SSE stream chunk-by-chunk and update the last message in place.
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        // SSE messages are separated by double-newlines.
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";

        for (const part of parts) {
          for (const line of part.split("\n")) {
            if (!line.startsWith("data: ")) continue;
            const raw = line.slice(6).trim();
            if (!raw) continue;

            let event: { type: string; text?: string };
            try { event = JSON.parse(raw); } catch { continue; }

            if (event.type === "token" && event.text) {
              setMessages((prev) => {
                const last = prev[prev.length - 1];
                // First token: insert a new assistant bubble.
                if (!last || last.role !== "assistant") {
                  return [...prev, { role: "assistant", content: event.text! }];
                }
                // Subsequent tokens: append to the existing bubble.
                const updated = [...prev];
                updated[updated.length - 1] = {
                  ...last,
                  content: last.content + event.text,
                };
                return updated;
              });
            } else if (event.type === "error" && event.text) {
              setMessages((prev) => {
                const last = prev[prev.length - 1];
                if (!last || last.role !== "assistant") {
                  return [...prev, { role: "assistant", content: `Error: ${event.text}` }];
                }
                const updated = [...prev];
                updated[updated.length - 1] = {
                  ...updated[updated.length - 1],
                  content: `Error: ${event.text}`,
                };
                return updated;
              });
            }
            // "progress" and "done" events need no UI action:
            // progress could drive a status label (future enhancement),
            // done is implicit when the stream closes.
          }
        }
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Error: ${err instanceof Error ? err.message : "Something went wrong."}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <>
      <style>{`
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(16px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes fadeIn {
          from { opacity: 0; }
          to   { opacity: 1; }
        }
        @keyframes glowPulse {
          0%, 100% { opacity: 0.5; }
          50%       { opacity: 0.85; }
        }
        @keyframes bounce-dot {
          0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
          40%            { transform: translateY(-5px); opacity: 1; }
        }

        .animate-fade-in { animation: fadeIn 0.6s ease both; }
        .animate-fade-up { animation: fadeUp 0.5s cubic-bezier(0.22,1,0.36,1) both; }

        .glow-orb { animation: glowPulse 6s ease-in-out infinite; }

        /* Noise */
        .noise-overlay::after {
          content: '';
          position: absolute;
          inset: 0;
          background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.035'/%3E%3C/svg%3E");
          background-repeat: repeat;
          background-size: 180px;
          pointer-events: none;
          z-index: 0;
        }

        /* Message entrance */
        .msg-enter {
          animation: fadeUp 0.35s cubic-bezier(0.22,1,0.36,1) both;
        }

        /* Scrollbar */
        .chat-scroll::-webkit-scrollbar { width: 4px; }
        .chat-scroll::-webkit-scrollbar-track { background: transparent; }
        .chat-scroll::-webkit-scrollbar-thumb {
          background: rgba(147,197,253,0.12);
          border-radius: 999px;
        }
        .chat-scroll::-webkit-scrollbar-thumb:hover {
          background: rgba(147,197,253,0.22);
        }

        /* Send button */
        .send-btn {
          transition: transform 0.15s ease, box-shadow 0.2s ease, background 0.2s ease;
        }
        .send-btn:hover:not(:disabled) {
          transform: translateY(-1px);
          box-shadow: 0 0 22px rgba(96,165,250,0.38), 0 4px 16px rgba(0,0,0,0.4);
          background: linear-gradient(135deg, rgba(96,165,250,0.28) 0%, rgba(167,139,250,0.24) 100%) !important;
        }
        .send-btn:active:not(:disabled) { transform: translateY(0); }

        /* Back button */
        .back-btn {
          transition: background 0.18s ease, color 0.18s ease;
        }
        .back-btn:hover {
          background: rgba(255,255,255,0.07) !important;
          color: rgba(255,255,255,0.9) !important;
        }

        /* Textarea */
        .chat-input {
          transition: border-color 0.2s ease, box-shadow 0.2s ease;
        }
        .chat-input:focus {
          border-color: rgba(96,165,250,0.35) !important;
          box-shadow: 0 0 0 3px rgba(96,165,250,0.08), 0 0 20px rgba(96,165,250,0.06);
          outline: none;
        }

        /* Dot bounce typing indicator */
        .dot-bounce {
          animation: bounce-dot 1.2s ease-in-out infinite;
        }
        .dot-bounce:nth-child(2) { animation-delay: 0.15s; }
        .dot-bounce:nth-child(3) { animation-delay: 0.30s; }

        /* Gradient text */
        .gradient-text {
          background: linear-gradient(135deg, #93c5fd 0%, #a5b4fc 50%, #c4b5fd 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }
      `}</style>

      <div
        className={`${onest.variable} relative flex h-screen w-full flex-col overflow-hidden bg-[#020408]`}
        style={{ fontFamily: "var(--font-onest), sans-serif" }}
      >
        {/* ── BACKGROUND ─────────────────────────────── */}
        <div className="noise-overlay pointer-events-none absolute inset-0 z-0">
          <div
            className="animate-fade-in absolute inset-0"
            style={{
              backgroundImage: "url('/earth-bg.png')",
              backgroundSize: "cover",
              backgroundPosition: "center bottom",
              backgroundRepeat: "no-repeat",
              opacity: 0.28,
            }}
          />
          {/* Heavy dark overlay — keep bg dim so chat is readable */}
          <div
            className="absolute inset-0"
            style={{
              background:
                "linear-gradient(to bottom, rgba(2,4,8,0.92) 0%, rgba(2,4,8,0.80) 50%, rgba(2,4,8,0.88) 100%)",
            }}
          />
          {/* Ambient top glow */}
          <div
            className="glow-orb absolute left-1/2 top-0 -translate-x-1/2"
            style={{
              width: "700px",
              height: "340px",
              borderRadius: "50%",
              background:
                "radial-gradient(ellipse, rgba(79,110,190,0.12) 0%, transparent 70%)",
              filter: "blur(48px)",
            }}
          />
          {/* Side flares */}
          <div
            className="absolute right-0 top-1/3"
            style={{
              width: "340px",
              height: "340px",
              borderRadius: "50%",
              background:
                "radial-gradient(ellipse, rgba(139,92,246,0.06) 0%, transparent 70%)",
              filter: "blur(60px)",
            }}
          />
          <div
            className="absolute bottom-0 left-0"
            style={{
              width: "380px",
              height: "260px",
              borderRadius: "50%",
              background:
                "radial-gradient(ellipse, rgba(59,130,246,0.05) 0%, transparent 70%)",
              filter: "blur(60px)",
            }}
          />
        </div>

        {/* ── HEADER ─────────────────────────────────── */}
        <header
          className="animate-fade-up relative z-20 flex shrink-0 items-center gap-3 border-b border-white/[0.06] px-5 py-4 md:px-8"
          style={{ backdropFilter: "blur(20px)", background: "rgba(2,4,8,0.55)" }}
        >
          {/* Back link */}
          <Link href="/">
            <button
              className="back-btn mr-1 flex h-8 w-8 items-center justify-center rounded-lg border border-white/[0.07] bg-white/[0.04] text-white/40"
            >
              <ArrowLeft size={14} strokeWidth={2} />
            </button>
          </Link>

          {/* Logo mark */}
          <div
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl"
            style={{
              background: "linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%)",
              boxShadow: "0 0 18px rgba(96,165,250,0.30)",
            }}
          >
            {/* hiring / people icon */}
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="h-5 w-5 text-white"
            >
              <path d="M10 9a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM6 8a2 2 0 1 1-4 0 2 2 0 0 1 4 0ZM1.49 15.326a.78.78 0 0 1-.358-.442 3 3 0 0 1 4.308-3.516 6.484 6.484 0 0 0-1.905 3.959c-.023.222-.014.442.025.654a4.97 4.97 0 0 1-2.07-.655ZM16.44 15.98a4.97 4.97 0 0 0 2.07-.654.78.78 0 0 0 .357-.442 3 3 0 0 0-4.308-3.517 6.484 6.484 0 0 1 1.907 3.96 2.32 2.32 0 0 1-.026.654ZM18 8a2 2 0 1 1-4 0 2 2 0 0 1 4 0ZM5.304 16.19a.844.844 0 0 1-.277-.71 5 5 0 0 1 9.947 0 .843.843 0 0 1-.277.71A6.975 6.975 0 0 1 10 18a6.974 6.974 0 0 1-4.696-1.81Z" />
            </svg>
          </div>

          <div className="min-w-0 flex-1">
            <h1 className="text-[14px] font-semibold leading-tight tracking-[-0.02em] text-white/90">
              Hiring Copilot
            </h1>
            <p className="text-[11px] font-light tracking-wide text-white/36">
              AI-powered hiring assistant
            </p>
          </div>

          {/* Status pill */}
          <div
            className="hidden items-center gap-1.5 rounded-full border border-white/[0.07] bg-white/[0.04] px-3 py-1 sm:flex"
            style={{ backdropFilter: "blur(8px)" }}
          >
            <span
              className="h-1.5 w-1.5 rounded-full bg-emerald-400"
              style={{ boxShadow: "0 0 6px rgba(52,211,153,0.8)" }}
            />
            <span className="text-[11px] font-medium tracking-wide text-white/40">
              Online
            </span>
          </div>
        </header>

        {/* ── MESSAGE LIST ───────────────────────────── */}
        <div className="chat-scroll relative z-10 flex-1 overflow-y-auto px-4 py-6 md:px-6">
          <div className="mx-auto flex max-w-3xl flex-col gap-5">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`msg-enter flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
                style={{ animationDelay: `${i * 0.04}s` }}
              >
                {/* Avatar */}
                <div
                  className={`relative shrink-0 flex h-8 w-8 items-center justify-center rounded-full text-[11px] font-bold ${
                    msg.role === "user" ? "" : ""
                  }`}
                  style={
                    msg.role === "user"
                      ? {
                          background:
                            "linear-gradient(135deg, #3b82f6 0%, #7c3aed 100%)",
                          boxShadow: "0 0 12px rgba(96,165,250,0.25)",
                        }
                      : {
                          background: "rgba(255,255,255,0.05)",
                          border: "1px solid rgba(255,255,255,0.09)",
                        }
                  }
                >
                  <span
                    className={
                      msg.role === "user"
                        ? "text-white"
                        : "text-white/55"
                    }
                  >
                    {msg.role === "user" ? "U" : "AI"}
                  </span>
                </div>

                {/* Bubble */}
                <div
                  className={`max-w-[78%] rounded-2xl px-4 py-3 text-[13.5px] leading-relaxed whitespace-pre-wrap tracking-[-0.01em] ${
                    msg.role === "user"
                      ? "rounded-tr-sm text-white"
                      : "rounded-tl-sm text-white/80"
                  }`}
                  style={
                    msg.role === "user"
                      ? {
                          background:
                            "linear-gradient(135deg, rgba(59,130,246,0.35) 0%, rgba(109,40,217,0.30) 100%)",
                          border: "1px solid rgba(96,165,250,0.18)",
                          backdropFilter: "blur(12px)",
                          boxShadow: "0 4px 20px rgba(0,0,0,0.25)",
                        }
                      : {
                          background: "rgba(255,255,255,0.035)",
                          border: "1px solid rgba(255,255,255,0.07)",
                          backdropFilter: "blur(14px)",
                          boxShadow: "0 4px 20px rgba(0,0,0,0.2)",
                        }
                  }
                >
                  {msg.content}
                </div>
              </div>
            ))}

            {/* Typing indicator */}
            {loading && (
              <div className="msg-enter flex gap-3 flex-row">
                <div
                  className="shrink-0 flex h-8 w-8 items-center justify-center rounded-full text-[11px] font-bold text-white/55"
                  style={{
                    background: "rgba(255,255,255,0.05)",
                    border: "1px solid rgba(255,255,255,0.09)",
                  }}
                >
                  AI
                </div>
                <div
                  className="flex items-center gap-1.5 rounded-2xl rounded-tl-sm px-4 py-3.5"
                  style={{
                    background: "rgba(255,255,255,0.035)",
                    border: "1px solid rgba(255,255,255,0.07)",
                    backdropFilter: "blur(14px)",
                  }}
                >
                  <span className="dot-bounce h-1.5 w-1.5 rounded-full bg-blue-400/60 inline-block" />
                  <span className="dot-bounce h-1.5 w-1.5 rounded-full bg-blue-400/60 inline-block" />
                  <span className="dot-bounce h-1.5 w-1.5 rounded-full bg-blue-400/60 inline-block" />
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>
        </div>

        {/* ── INPUT BAR ──────────────────────────────── */}
        <div
          className="relative z-20 shrink-0 border-t border-white/[0.06] px-4 py-4 md:px-6"
          style={{ backdropFilter: "blur(20px)", background: "rgba(2,4,8,0.60)" }}
        >
          <form
            onSubmit={handleSend}
            className="mx-auto flex max-w-3xl items-end gap-3"
          >
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about candidates, rankings, or job fit…"
              rows={1}
              disabled={loading}
              className="chat-input flex-1 resize-none rounded-xl border border-white/[0.09] bg-white/[0.045] px-4 py-3 text-[13.5px] font-light leading-relaxed text-white placeholder-white/25 transition disabled:opacity-50"
              style={{
                backdropFilter: "blur(14px)",
                fieldSizing: "content",
                maxHeight: "144px",
                overflowY: "auto",
                fontFamily: "var(--font-onest), sans-serif",
              } as React.CSSProperties}
            />

            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="send-btn shrink-0 flex h-11 w-11 items-center justify-center rounded-xl border border-blue-400/20 text-white disabled:cursor-not-allowed disabled:opacity-30"
              style={{
                background:
                  "linear-gradient(135deg, rgba(59,130,246,0.2) 0%, rgba(109,40,217,0.18) 100%)",
                backdropFilter: "blur(14px)",
              }}
            >
              <Send size={15} strokeWidth={2} className="translate-x-[1px]" />
            </button>
          </form>

          <p className="mx-auto mt-2.5 max-w-3xl text-center text-[11px] font-light tracking-wide text-white/18">
            Enter to send &nbsp;·&nbsp; Shift + Enter for new line
          </p>
        </div>
      </div>
    </>
  );
}