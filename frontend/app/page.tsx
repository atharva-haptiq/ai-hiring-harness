import Link from "next/link";
import { Onest } from "next/font/google";
import {
  MessageSquare,
  Layers,
  BarChart3,
  ShieldCheck,
} from "lucide-react";

const onest = Onest({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700", "800", "900"],
  variable: "--font-onest",
});

const features = [
  {
    icon: MessageSquare,
    title: "Conversational AI",
    desc: "Natural conversations, powerful actions.",
  },
  {
    icon: Layers,
    title: "End-to-End Hiring",
    desc: "From job creation to outreach — in one flow.",
  },
  {
    icon: BarChart3,
    title: "Intelligent Ranking",
    desc: "AI scores and explains candidate fit.",
  },
  {
    icon: ShieldCheck,
    title: "Private & Local",
    desc: "Your data stays secure, your way.",
  },
];

export default function HomePage() {
  return (
    <>
      <style>{`
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(24px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes fadeIn {
          from { opacity: 0; }
          to   { opacity: 1; }
        }
        @keyframes badgePulse {
          0%, 100% { box-shadow: 0 0 0 0 rgba(99,179,237,0.18); }
          50%       { box-shadow: 0 0 18px 4px rgba(99,179,237,0.22); }
        }
        @keyframes glowPulse {
          0%, 100% { opacity: 0.55; }
          50%       { opacity: 0.85; }
        }
        .animate-fade-up-1 { animation: fadeUp 0.75s cubic-bezier(0.22,1,0.36,1) 0.05s both; }
        .animate-fade-up-2 { animation: fadeUp 0.75s cubic-bezier(0.22,1,0.36,1) 0.18s both; }
        .animate-fade-up-3 { animation: fadeUp 0.75s cubic-bezier(0.22,1,0.36,1) 0.30s both; }
        .animate-fade-up-4 { animation: fadeUp 0.75s cubic-bezier(0.22,1,0.36,1) 0.42s both; }
        .animate-fade-up-5 { animation: fadeUp 0.75s cubic-bezier(0.22,1,0.36,1) 0.54s both; }
        .animate-fade-up-6 { animation: fadeUp 0.75s cubic-bezier(0.22,1,0.36,1) 0.66s both; }
        .animate-fade-in  { animation: fadeIn 1.1s ease 0.1s both; }

        .badge-glow { animation: badgePulse 3s ease-in-out infinite; }

        .gradient-text {
          background: linear-gradient(135deg, #93c5fd 0%, #a5b4fc 40%, #c4b5fd 80%, #f0abfc 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }

        .cta-btn {
          position: relative;
          overflow: hidden;
          transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .cta-btn::before {
          content: '';
          position: absolute;
          inset: 0;
          background: linear-gradient(135deg, rgba(147,197,253,0.12) 0%, rgba(196,181,253,0.18) 100%);
          opacity: 0;
          transition: opacity 0.25s ease;
        }
        .cta-btn:hover::before { opacity: 1; }
        .cta-btn:hover {
          transform: translateY(-2px);
          box-shadow: 0 0 32px rgba(147,197,253,0.28), 0 8px 32px rgba(0,0,0,0.35);
        }
        .cta-btn:active { transform: translateY(0px); }

        .open-btn {
          transition: background 0.2s ease, box-shadow 0.2s ease, transform 0.15s ease;
        }
        .open-btn:hover {
          background: rgba(255,255,255,0.12) !important;
          box-shadow: 0 0 14px rgba(147,197,253,0.2);
          transform: translateY(-1px);
        }

        .feature-card {
          transition: background 0.25s ease, border-color 0.25s ease, transform 0.25s ease;
        }
        .feature-card:hover {
          background: rgba(255,255,255,0.055) !important;
          border-color: rgba(147,197,253,0.18) !important;
          transform: translateY(-3px);
        }

        .glow-orb {
          animation: glowPulse 5s ease-in-out infinite;
        }

        /* Noise texture overlay */
        .noise-overlay::after {
          content: '';
          position: absolute;
          inset: 0;
          background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E");
          background-repeat: repeat;
          background-size: 180px;
          pointer-events: none;
          z-index: 1;
        }

        /* Scanline shimmer */
        .scanlines::before {
          content: '';
          position: absolute;
          inset: 0;
          background: repeating-linear-gradient(
            0deg,
            transparent,
            transparent 2px,
            rgba(255,255,255,0.008) 2px,
            rgba(255,255,255,0.008) 4px
          );
          pointer-events: none;
          z-index: 1;
        }
      `}</style>

      <main
        className={`${onest.variable} relative min-h-screen w-full overflow-hidden bg-[#020408] text-white`}
        style={{ fontFamily: "var(--font-onest), sans-serif" }}
      >
        {/* ── BACKGROUND ─────────────────────────────────────── */}
        <div className="noise-overlay scanlines absolute inset-0 z-0">
          {/* Earth hero image */}
          <div
            className="animate-fade-in absolute inset-0"
            style={{
              backgroundImage: "url('/earth-bg.png')",
              backgroundSize: "cover",
              backgroundPosition: "center bottom",
              backgroundRepeat: "no-repeat",
            }}
          />

          {/* Multi-layer dark overlay */}
          <div
            className="absolute inset-0"
            style={{
              background:
                "linear-gradient(to bottom, rgba(2,4,8,0.82) 0%, rgba(2,4,8,0.52) 38%, rgba(2,4,8,0.35) 58%, rgba(2,4,8,0.72) 100%)",
            }}
          />

          {/* Top vignette */}
          <div
            className="absolute inset-x-0 top-0 h-48"
            style={{
              background:
                "linear-gradient(to bottom, rgba(2,4,8,0.95), transparent)",
            }}
          />

          {/* Ambient top-center glow */}
          <div
            className="glow-orb absolute left-1/2 top-0 -translate-x-1/2"
            style={{
              width: "720px",
              height: "380px",
              borderRadius: "50%",
              background:
                "radial-gradient(ellipse, rgba(99,130,200,0.13) 0%, transparent 70%)",
              filter: "blur(40px)",
            }}
          />

          {/* Subtle blue side flares */}
          <div
            className="absolute left-0 top-1/4 -translate-y-1/2"
            style={{
              width: "420px",
              height: "420px",
              borderRadius: "50%",
              background:
                "radial-gradient(ellipse, rgba(59,130,246,0.06) 0%, transparent 70%)",
              filter: "blur(60px)",
            }}
          />
          <div
            className="absolute right-0 top-1/3 -translate-y-1/2"
            style={{
              width: "380px",
              height: "380px",
              borderRadius: "50%",
              background:
                "radial-gradient(ellipse, rgba(139,92,246,0.06) 0%, transparent 70%)",
              filter: "blur(60px)",
            }}
          />
        </div>

        {/* ── NAVBAR ─────────────────────────────────────────── */}
        <nav
          className="animate-fade-up-1 relative z-20 flex items-center justify-between px-6 py-5 md:px-10 lg:px-16"
        >
          {/* Logo */}
          <div className="flex items-center gap-2.5">
            <div
              className="h-7 w-7 rounded-lg"
              style={{
                background:
                  "linear-gradient(135deg, #60a5fa 0%, #a78bfa 100%)",
                boxShadow: "0 0 14px rgba(96,165,250,0.35)",
              }}
            />
            <span
              className="text-[15px] font-semibold tracking-[-0.02em] text-white/90"
            >
              Hiring Copilot
            </span>
          </div>

          {/* CTA nav button */}
          <Link href="/copilot">
            <button
              className="open-btn rounded-lg border border-white/10 bg-white/7 px-4 py-1.5 text-[13px] font-medium tracking-tight text-white/80"
              style={{ backdropFilter: "blur(12px)" }}
            >
              Open Copilot
            </button>
          </Link>
        </nav>

        {/* ── HERO ───────────────────────────────────────────── */}
        <section className="relative z-10 flex flex-col items-center px-6 pt-10 pb-0 text-center md:pt-16 lg:pt-20">

          {/* Top badge */}
          <div className="animate-fade-up-1 mb-7">
            <span
              className="badge-glow inline-flex items-center gap-2 rounded-full border border-blue-400/20 bg-blue-500/8 px-4 py-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] text-blue-300/80"
              style={{ backdropFilter: "blur(10px)" }}
            >
              <span
                className="h-1.5 w-1.5 rounded-full bg-blue-400"
                style={{ boxShadow: "0 0 6px rgba(96,165,250,0.8)" }}
              />
              AI Agent Harness
            </span>
          </div>

          {/* Main headline */}
          <h1
            className="animate-fade-up-2 max-w-3xl text-[clamp(40px,7vw,82px)] font-black leading-[1.03] tracking-[-0.04em] text-white"
          >
            Your AI Copilot
            <br />
            <span className="gradient-text">for Smarter Hiring</span>
          </h1>

          {/* Subheadline */}
          <p
            className="animate-fade-up-3 mt-6 max-w-md text-[clamp(15px,1.6vw,17px)] font-light leading-relaxed tracking-[-0.01em] text-white/50"
          >
            Conversational AI that understands hiring,
            <br className="hidden sm:block" />
            ranks candidates, and gets work done.
          </p>

          {/* CTA */}
          <div className="animate-fade-up-4 mt-10 flex flex-col items-center gap-3">
            <Link href="/copilot">
              <button
                className="cta-btn rounded-xl border border-blue-400/25 bg-gradient-to-r from-blue-500/15 to-violet-500/15 px-8 py-3.5 text-[15px] font-semibold tracking-[-0.02em] text-white"
                style={{
                  backdropFilter: "blur(16px)",
                  boxShadow:
                    "0 0 0 1px rgba(147,197,253,0.08) inset, 0 4px 24px rgba(0,0,0,0.3)",
                }}
              >
                Open Copilot Chat →
              </button>
            </Link>
            <span className="text-[12px] font-light tracking-wide text-white/28">
              Start a conversation → get things done
            </span>
          </div>

          {/* ── FEATURE ROW ────────────────────────────────────── */}
          <div
            className="animate-fade-up-5 mt-16 grid w-full max-w-4xl grid-cols-2 gap-3 px-0 md:mt-20 md:grid-cols-4 md:gap-4"
          >
            {features.map(({ icon: Icon, title, desc }) => (
              <div
                key={title}
                className="feature-card rounded-2xl border border-white/[0.065] bg-white/[0.032] p-4 text-left md:p-5"
                style={{ backdropFilter: "blur(14px)" }}
              >
                <div
                  className="mb-3 inline-flex h-8 w-8 items-center justify-center rounded-lg"
                  style={{
                    background:
                      "linear-gradient(135deg, rgba(96,165,250,0.18) 0%, rgba(167,139,250,0.14) 100%)",
                    border: "1px solid rgba(147,197,253,0.14)",
                  }}
                >
                  <Icon
                    size={15}
                    strokeWidth={1.8}
                    className="text-blue-300/80"
                  />
                </div>
                <p className="mb-1 text-[13px] font-semibold tracking-[-0.02em] text-white/88">
                  {title}
                </p>
                <p className="text-[12px] font-light leading-relaxed text-white/40">
                  {desc}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* ── FOOTER ─────────────────────────────────────────── */}
        <footer className="animate-fade-up-6 relative z-10 mt-10 pb-7 text-center md:mt-12">
          <p className="text-[11px] font-light tracking-[0.1em] text-white/22 uppercase">
            AI Hiring Copilot &nbsp;•&nbsp; Built for Recruiters &nbsp;•&nbsp; Powered by AI
          </p>
        </footer>

        {/* ── BOTTOM FADE (into earth glow) ─── */}
        <div
          className="pointer-events-none absolute bottom-0 inset-x-0 z-5 h-40"
          style={{
            background:
              "linear-gradient(to top, rgba(2,4,8,0.55), transparent)",
          }}
        />
      </main>
    </>
  );
}