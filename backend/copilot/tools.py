"""
tools.py — Tool wrappers that expose core hiring harness functions as
plain Python callables returning dictionaries.

These are used by the orchestrator to execute actions after the LLM
has classified the recruiter's intent and extracted entities.

All functions open their own database session and close it on exit
so they can be called independently of the FastAPI request lifecycle.
"""

import asyncio
import json
import re
import sys
from pathlib import Path

# Allow imports from the backend root (db, models, etc.)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db import SessionLocal
from models import Candidate, Job

# ---------------------------------------------------------------------------
# LLM scoring prompt
# ---------------------------------------------------------------------------

_RANK_PROMPT_TEMPLATE = """\
You are an expert technical recruiter evaluating candidate fit for a job.

JOB TITLE: {title}

JOB DESCRIPTION:
{jd_text}

CANDIDATE RESUME:
{resume_text}

Evaluate the candidate on the following dimensions:
  1. Skills match       — Do their listed skills align with what the JD requires?
  2. Experience level   — Do they have enough years and depth of experience?
  3. Seniority fit      — Does their career level match the role's expectations?
  4. Domain relevance   — Is their industry/domain background relevant to this role?

Return ONLY a valid JSON object with no markdown, no explanation:
{{
  "score": <integer 0-100>,
  "explanation": "<2-3 sentence plain English summary of fit>"
}}

Score guide: 0-30 poor fit, 31-60 partial fit, 61-85 good fit, 86-100 excellent fit.
"""


async def _llm_score_candidate(resume_text: str, job_title: str, jd_text: str) -> tuple[float, str]:
    """
    Use the local LLM to score a candidate against a job description.

    Evaluates skills, experience, seniority, and domain relevance.
    Falls back to keyword scoring if the LLM is unavailable or returns
    unparseable output.

    Args:
        resume_text -- Full extracted text from the candidate's PDF.
        job_title   -- Title of the job role.
        jd_text     -- Full job description text.

    Returns:
        Tuple of (score: float 0-100, explanation: str).
    """
    # Truncate to keep the prompt within a manageable context window on CPU.
    # Large resumes (10+ pages) slow generation dramatically; 3000 chars
    # captures the most relevant skills and experience sections.
    resume_snippet = resume_text[:3000].strip()
    jd_snippet = jd_text[:1500].strip()

    prompt = _RANK_PROMPT_TEMPLATE.format(
        title=job_title,
        jd_text=jd_snippet,
        resume_text=resume_snippet,
    )

    try:
        from copilot.llm import ask_llm
        # num_predict=256 caps output tokens — a score + 2-sentence explanation
        # needs fewer than 100 tokens; the cap prevents runaway generation on CPU.
        raw = await ask_llm(prompt, num_predict=256)
    except RuntimeError:
        # LLM unavailable — fall back to keyword scoring
        return _keyword_fallback(resume_text, jd_text)

    # Try to parse JSON from the response
    text = raw.strip()
    for candidate_json in [text, _extract_json_block(text)]:
        if candidate_json is None:
            continue
        try:
            data = json.loads(candidate_json)
            score = float(data.get("score", 0))
            score = max(0.0, min(100.0, score))  # Clamp to 0-100
            explanation = str(data.get("explanation", "")).strip()
            if explanation:
                return round(score, 1), explanation
        except (json.JSONDecodeError, ValueError, TypeError):
            continue

    # JSON parse failed — fall back to keyword scoring
    return _keyword_fallback(resume_text, jd_text)


def _extract_json_block(text: str) -> str | None:
    """Extract the first {...} block from a string (handles markdown fences)."""
    match = re.search(r'\{.*\}', text, re.DOTALL)
    return match.group(0) if match else None


def _keyword_fallback(resume_text: str, jd_text: str) -> tuple[float, str]:
    """Keyword-based score used when the LLM is unavailable."""
    keywords = _extract_keywords(jd_text)
    if not keywords:
        return 0.0, "Could not evaluate — no keywords found in job description."
    score, matched = _score_resume(resume_text, keywords)
    if matched:
        explanation = f"Keyword match fallback: matched {len(matched)} term(s) including {', '.join(matched[:3])}."
    else:
        explanation = "Keyword match fallback: no matching terms found in resume."
    return score, explanation


_OUTREACH_PROMPT_TEMPLATE = """\
You are a professional technical recruiter writing a personalized outreach email.

JOB TITLE: {title}

JOB DESCRIPTION (summary):
{jd_snippet}

CANDIDATE PROFILE:
  Name: {name}
  Email: {email}
  Resume excerpt:
{resume_snippet}

Write a concise, warm, and professional recruiter outreach email to this candidate \
for the above role.

Requirements:
  - Address the candidate by name if available, otherwise use a friendly greeting.
  - Mention 1-2 specific aspects of their background that make them a strong fit.
  - Briefly describe the opportunity without overselling.
  - End with a clear, low-pressure call to action (e.g., a short call).
  - Tone: professional, human, and respectful of the candidate's time.
  - Length: 150-220 words.

Return ONLY a JSON object with no markdown, no explanation:
{{
  "subject": "<email subject line>",
  "body": "<full email body>"
}}
"""

# Fallback template used when the LLM is unavailable
_OUTREACH_SUBJECT_FALLBACK = "Exciting {role} Opportunity — Would Love to Connect"
_OUTREACH_BODY_FALLBACK = """\
Hi {name},

I hope this message finds you well. My name is [Your Name], and I'm a recruiter \
working to fill the {role} role at [Company Name].

Having reviewed your background, I believe your experience aligns well with what \
we're looking for — particularly {highlights}.

This is a full-time position offering a collaborative environment, competitive \
compensation, and real ownership of meaningful work.

If you're open to a brief conversation, I'd love to share more details.

Best regards,
[Your Name] | [Company Name]
"""


# ---------------------------------------------------------------------------
# Plain-text outreach prompt — used by stream_copilot so tokens can be
# streamed directly to the UI without waiting to parse a JSON wrapper.
# ---------------------------------------------------------------------------
_OUTREACH_PLAINTEXT_PROMPT_TEMPLATE = """\
You are a professional technical recruiter writing a personalized outreach email.

JOB TITLE: {title}

JOB DESCRIPTION (summary):
{jd_snippet}

CANDIDATE PROFILE:
  Name: {name}
  Email: {email}
  Resume excerpt:
{resume_snippet}

Write a concise, warm, and professional recruiter outreach email.

Requirements:
  - Start your response with exactly: Subject: <subject line>
  - Then leave one blank line, then write the email body.
  - Address the candidate by name, mention 1-2 specific aspects of their background.
  - Briefly describe the opportunity and end with a clear call to action.
  - 150-220 words. No JSON, no code blocks, no extra commentary.
"""


def build_outreach_plaintext_prompt(
    candidate_name: str | None,
    candidate_email: str | None,
    resume_text: str,
    job_title: str,
    jd_text: str,
) -> str:
    """Return the plain-text outreach prompt used for streaming."""
    return _OUTREACH_PLAINTEXT_PROMPT_TEMPLATE.format(
        title=job_title,
        jd_snippet=jd_text[:800].strip(),
        name=candidate_name or "there",
        email=candidate_email or "(not available)",
        resume_snippet=resume_text[:2000].strip(),
    )


async def _llm_generate_outreach(
    candidate_name: str | None,
    candidate_email: str | None,
    resume_text: str,
    job_title: str,
    jd_text: str,
) -> tuple[str, str]:
    """
    Use the local LLM to write a personalised recruiter outreach email.

    Falls back to the static template if the LLM is unavailable or returns
    unparseable output.

    Returns:
        Tuple of (subject: str, body: str).
    """
    name_display = candidate_name or "there"
    resume_snippet = resume_text[:2000].strip()
    jd_snippet = jd_text[:800].strip()

    prompt = _OUTREACH_PROMPT_TEMPLATE.format(
        title=job_title,
        jd_snippet=jd_snippet,
        name=name_display,
        email=candidate_email or "(not available)",
        resume_snippet=resume_snippet,
    )

    try:
        from copilot.llm import ask_llm
        # num_predict=512: outreach emails are ~150-220 words; cap prevents
        # the model from adding unwanted commentary after the JSON object.
        raw = await ask_llm(prompt, num_predict=512)
    except RuntimeError:
        return _outreach_template_fallback(candidate_name, job_title, resume_text, jd_text)

    for candidate_json in [raw.strip(), _extract_json_block(raw)]:
        if candidate_json is None:
            continue
        try:
            data = json.loads(candidate_json)
            subject = str(data.get("subject", "")).strip()
            body = str(data.get("body", "")).strip()
            if subject and body:
                return subject, body
        except (json.JSONDecodeError, ValueError, TypeError):
            continue

    return _outreach_template_fallback(candidate_name, job_title, resume_text, jd_text)


def _outreach_template_fallback(
    candidate_name: str | None,
    job_title: str,
    resume_text: str,
    jd_text: str,
) -> tuple[str, str]:
    """Static template fallback used when the LLM is unavailable."""
    keywords = _extract_keywords(jd_text, top_n=10)
    matched = [
        kw for kw in keywords
        if re.search(r'\b' + re.escape(kw) + r'\b', resume_text.lower())
    ]
    highlights = f"your experience with {', '.join(matched[:3])}" if matched else "your professional background"
    name = candidate_name or "there"
    subject = _OUTREACH_SUBJECT_FALLBACK.format(role=job_title)
    body = _OUTREACH_BODY_FALLBACK.format(name=name, role=job_title, highlights=highlights)
    return subject, body.strip()

_STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "is", "are", "was", "be", "by", "as", "we", "you",
    "our", "your", "will", "must", "have", "has", "can", "may", "this",
    "that", "from", "not", "it", "its", "they", "their", "about", "also",
    "able", "such", "both", "more", "into", "than", "who", "what",
}


def _extract_keywords(text: str, top_n: int = 30) -> list[str]:
    words = re.findall(r'[a-z]+', text.lower())
    filtered = [w for w in words if w not in _STOP_WORDS and len(w) > 2]
    freq: dict[str, int] = {}
    for w in filtered:
        freq[w] = freq.get(w, 0) + 1
    return sorted(freq, key=lambda w: freq[w], reverse=True)[:top_n]


def _score_resume(resume_text: str, keywords: list[str]) -> tuple[float, list[str]]:
    lower = resume_text.lower()
    matched = [kw for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', lower)]
    score = round((len(matched) / len(keywords)) * 100, 1) if keywords else 0.0
    return score, matched


# ---------------------------------------------------------------------------
# Tool functions
# ---------------------------------------------------------------------------

def create_job_tool(title: str, jd_text: str) -> dict:
    """
    Create a new job posting and persist it to the database.

    Args:
        title   -- Job title (e.g. "Senior Backend Engineer").
        jd_text -- Full job description text.

    Returns:
        On success: { "ok": True, "job": { id, title, jd_text, created_at } }
        On failure: { "ok": False, "error": "<message>" }
    """
    if not title or not title.strip():
        return {"ok": False, "error": "title is required"}
    if not jd_text or not jd_text.strip():
        return {"ok": False, "error": "jd_text is required"}

    db = SessionLocal()
    try:
        job = Job(title=title.strip(), jd_text=jd_text.strip())
        db.add(job)
        db.commit()
        db.refresh(job)
        return {
            "ok": True,
            "job": {
                "id": job.id,
                "title": job.title,
                "jd_text": job.jd_text,
                "created_at": job.created_at.isoformat(),
            },
        }
    except Exception as exc:
        db.rollback()
        return {"ok": False, "error": str(exc)}
    finally:
        db.close()


async def rank_candidates_tool(job_id: int) -> dict:
    """
    Score all candidates against a job using the local LLM.

    All candidate scoring coroutines are submitted to asyncio.gather so the
    server stays non-blocking while Ollama processes each one.
    On a CPU-only machine Ollama queues requests, so total wall time is
    approximately N * single_score_time, but the FastAPI event loop never
    freezes — other HTTP requests continue to be served in parallel.

    Args:
        job_id -- ID of the job to rank candidates against.

    Returns:
        On success: {
            "ok": True,
            "job": { id, title },
            "candidates": [{ id, name, email, score, explanation }, ...]
        }
        On failure: { "ok": False, "error": "<message>" }
    """
    # --- Load job + candidates synchronously (fast SQLite reads) ---
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            return {"ok": False, "error": f"Job {job_id} not found"}

        candidates = db.query(Candidate).all()
        if not candidates:
            return {"ok": False, "error": "No candidates in database"}

        job_title = job.title
        jd_text = job.jd_text
        # Snapshot candidate data before closing the session so we don't
        # hold a DB connection while waiting for slow LLM responses.
        candidate_data = [
            {"id": c.id, "name": c.name, "email": c.email, "resume_text": c.resume_text}
            for c in candidates
        ]
    finally:
        db.close()

    # --- Score all candidates concurrently (non-blocking) ---
    async def _score_one(cdata: dict) -> dict:
        score, explanation = await _llm_score_candidate(
            cdata["resume_text"], job_title, jd_text
        )
        return {
            "id": cdata["id"],
            "name": cdata["name"],
            "email": cdata["email"],
            "score": score,
            "explanation": explanation,
        }

    results = list(await asyncio.gather(*[_score_one(c) for c in candidate_data]))

    # --- Persist updated scores in a fresh session ---
    db2 = SessionLocal()
    try:
        for r in results:
            candidate = db2.get(Candidate, r["id"])
            if candidate:
                candidate.score = r["score"]
                db2.add(candidate)
        db2.commit()
    except Exception as exc:
        db2.rollback()
        return {"ok": False, "error": str(exc)}
    finally:
        db2.close()

    results.sort(key=lambda c: c["score"], reverse=True)
    return {
        "ok": True,
        "job": {"id": job_id, "title": job_title},
        "candidates": results,
    }


async def generate_outreach_tool(candidate_id: int, job_id: int) -> dict:
    """
    Generate a personalised recruiter outreach email using the local LLM.

    Falls back to a static template if the LLM is unavailable or returns
    unparseable output.

    Args:
        candidate_id -- ID of the candidate to contact.
        job_id       -- ID of the job to reference in the email.

    Returns:
        On success: { "ok": True, "subject": "...", "body": "..." }
        On failure: { "ok": False, "error": "<message>" }
    """
    db = SessionLocal()
    try:
        candidate = db.get(Candidate, candidate_id)
        if not candidate:
            return {"ok": False, "error": f"Candidate {candidate_id} not found"}

        job = db.get(Job, job_id)
        if not job:
            return {"ok": False, "error": f"Job {job_id} not found"}

        subject, body = await _llm_generate_outreach(
            candidate_name=candidate.name,
            candidate_email=candidate.email,
            resume_text=candidate.resume_text,
            job_title=job.title,
            jd_text=job.jd_text,
        )
        return {"ok": True, "subject": subject, "body": body}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        db.close()


def status_tool() -> dict:
    """
    Return a summary of the current state of the hiring harness database.

    Returns:
        On success: {
            "ok": True,
            "jobs": <count>,
            "candidates": <count>,
            "scored_candidates": <count>,
            "recent_jobs": [{ id, title, created_at }, ...]  # up to 5
        }
        On failure: { "ok": False, "error": "<message>" }
    """
    db = SessionLocal()
    try:
        job_count = db.query(Job).count()
        candidate_count = db.query(Candidate).count()
        scored_count = db.query(Candidate).filter(Candidate.score.isnot(None)).count()

        recent_jobs = [
            {
                "id": j.id,
                "title": j.title,
                "created_at": j.created_at.isoformat(),
            }
            for j in db.query(Job).order_by(Job.id.desc()).limit(5).all()
        ]

        return {
            "ok": True,
            "jobs": job_count,
            "candidates": candidate_count,
            "scored_candidates": scored_count,
            "recent_jobs": recent_jobs,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        db.close()
