"""
main.py — FastAPI application entry point.

Routes defined here:
    GET  /              -- Health check.
    POST /job/create    -- Create a new job posting.
    POST /resume/upload -- Upload one or more PDF resumes and persist candidates.
    POST /rank          -- Score and rank all candidates against a job description.
    POST /outreach      -- Generate a personalized recruiter outreach email.
    POST /copilot/chat  -- Natural language interface to the hiring harness.
"""

import io
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pdfplumber
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from db import Base, engine, SessionLocal
from models import Job, Candidate
from copilot.orchestrator import run_copilot, stream_copilot

# Directory where uploaded PDF files are stored on disk.
# Resolved relative to this file so it works regardless of the working directory.
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Create all tables defined in models.py if they don't already exist.
# Safe to call on every startup — it is a no-op when tables are present.
Base.metadata.create_all(bind=engine)

app = FastAPI()


def get_db():
    """
    FastAPI dependency that provides a SQLAlchemy database session.

    Yields a session for the duration of the request, then closes it
    in the finally block regardless of whether the request succeeded.
    Inject with `db: Session = Depends(get_db)` in route functions.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class JobCreate(BaseModel):
    """Request body for POST /job/create."""
    title: str    # Short role title
    jd_text: str  # Full job description text


class JobResponse(BaseModel):
    """Response body returned after a job is created."""
    id: int
    title: str
    jd_text: str
    created_at: datetime

    class Config:
        from_attributes = True  # Allow reading values from SQLAlchemy ORM objects


class CandidateResponse(BaseModel):
    """Response body for a single candidate after resume upload."""
    id: int
    name: Optional[str]         # None if name could not be inferred
    email: Optional[str]        # None if no email was found in the resume
    resume_text: str
    resume_path: Optional[str]  # Relative path to stored PDF file
    score: Optional[float]      # None until AI scoring is run
    created_at: datetime

    class Config:
        from_attributes = True  # Allow reading values from SQLAlchemy ORM objects


def _infer_name(text: str) -> Optional[str]:
    """
    Attempt to infer the candidate's full name from the top of their resume.

    Strategy: scan the first 10 lines and return the first line that:
      - Is between 4 and 60 characters (filters out single words and long paragraphs)
      - Contains no digits, @, |, /, or \ (filters emails, URLs, phone numbers)
      - Is not a long all-caps string (filters section headings like "WORK EXPERIENCE")

    Returns None if no suitable line is found.
    """
    for line in text.splitlines()[:10]:
        line = line.strip()
        # Skip very short or very long lines
        if 3 < len(line) < 60 and not re.search(r'[\d@|/\\]', line):
            # Skip lines that look like section headers (long all-caps strings)
            if not (line.isupper() and len(line) > 20):
                return line
    return None


def _infer_email(text: str) -> Optional[str]:
    """
    Extract the first email address found anywhere in the resume text.

    Uses a simple regex that covers the most common email formats.
    Returns None if no email address is present.
    """
    match = re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', text)
    return match.group(0) if match else None


@app.get("/")
def root():
    return {"status": "AI Hiring Harness Running"}


@app.post("/resume/upload", status_code=201)
async def upload_resumes(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload one or more PDF resumes and save each as a Candidate record.

    Accepts: multipart/form-data with field name `files` (multiple files allowed).

    Processing per file:
      1. Reject non-PDFs immediately.
      2. Parse PDF bytes with pdfplumber and join all page text.
      3. Reject PDFs with no extractable text (e.g. scanned image-only documents).
      4. Infer candidate name and email from the extracted text.
      5. Save the raw PDF to uploads/<uuid>.pdf on disk.
      6. Save Candidate (including resume_path) to the database.

    Errors are non-fatal — a failure on one file does not stop processing the rest.

    Returns:
        uploaded_count -- Number of candidates successfully saved.
        candidates     -- List of results; successful saves are full CandidateResponse
                          objects, failures are { filename, error } dicts.
    """
    saved: list[dict] = []

    for upload in files:
        # Reject files that are clearly not PDFs based on their MIME type.
        # application/octet-stream is included because some clients send it as a fallback.
        if upload.content_type not in ("application/pdf", "application/octet-stream"):
            saved.append({"filename": upload.filename, "error": "Not a PDF"})
            continue

        # Read raw bytes from the upload into memory (no temp file on disk).
        raw = await upload.read()
        try:
            # Wrap bytes in BytesIO so pdfplumber can treat it as a file-like object.
            with pdfplumber.open(io.BytesIO(raw)) as pdf:
                # Extract text from every page; default to empty string if a page has none.
                pages_text = [page.extract_text() or "" for page in pdf.pages]
            resume_text = "\n".join(pages_text).strip()
        except Exception:
            # Catches corrupt, password-protected, or non-PDF bytes.
            saved.append({"filename": upload.filename, "error": "Failed to parse PDF"})
            continue

        # Scanned (image-only) PDFs produce no text — skip them.
        if not resume_text:
            saved.append({"filename": upload.filename, "error": "No extractable text found"})
            continue

        # Heuristically extract candidate metadata from the resume text.
        name = _infer_name(resume_text)
        email = _infer_email(resume_text)

        # Save the raw PDF to disk with a UUID filename to avoid collisions
        # and prevent any path-traversal issues from the original filename.
        pdf_filename = f"{uuid.uuid4()}.pdf"
        pdf_path = UPLOAD_DIR / pdf_filename
        try:
            pdf_path.write_bytes(raw)
        except OSError:
            saved.append({"filename": upload.filename, "error": "Failed to save PDF to disk"})
            continue

        # resume_path stored as a relative string so it stays portable
        candidate = Candidate(
            name=name,
            email=email,
            resume_text=resume_text,
            resume_path=f"uploads/{pdf_filename}",
        )
        try:
            db.add(candidate)
            db.commit()
            # Refresh loads the server-generated id and created_at back onto the object.
            db.refresh(candidate)
        except Exception:
            db.rollback()  # Undo the failed insert before moving to the next file.
            saved.append({"filename": upload.filename, "error": "Database error"})
            continue

        # Serialize the ORM object to a plain dict for the response.
        saved.append(CandidateResponse.model_validate(candidate).model_dump())

    # Count only entries that don't have an "error" key.
    successful = [r for r in saved if "error" not in r]
    return {"uploaded_count": len(successful), "candidates": saved}


# Common English stop-words to exclude when extracting keywords from a job description.
# Keeping these in the match would inflate scores with meaningless function words.
_STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "is", "are", "was", "be", "by", "as", "we", "you",
    "our", "your", "will", "must", "have", "has", "can", "may", "this",
    "that", "from", "not", "it", "its", "they", "their", "about", "also",
    "able", "such", "both", "more", "into", "than", "who", "what",
}


def _extract_keywords(text: str, top_n: int = 30) -> list[str]:
    """
    Extract the most significant keywords from a block of text.

    Steps:
      1. Lowercase and tokenise into alphabetic words (strips punctuation).
      2. Remove stop-words and words shorter than 3 characters.
      3. Return the top_n most frequent words, preserving importance order.

    Args:
        text   -- Source text (e.g. job description).
        top_n  -- Maximum number of keywords to return.

    Returns:
        List of keyword strings, most frequent first.
    """
    words = re.findall(r'[a-z]+', text.lower())
    # Filter stop-words and very short tokens
    filtered = [w for w in words if w not in _STOP_WORDS and len(w) > 2]

    # Count frequency and return the top_n by count
    freq: dict[str, int] = {}
    for w in filtered:
        freq[w] = freq.get(w, 0) + 1
    sorted_words = sorted(freq, key=lambda w: freq[w], reverse=True)
    return sorted_words[:top_n]


def _score_resume(resume_text: str, keywords: list[str]) -> tuple[float, list[str]]:
    """
    Score a resume against a list of keywords extracted from a job description.

    Scoring:
      - Each keyword that appears in the resume text (case-insensitive) counts as a match.
      - Score = (matched_keywords / total_keywords) * 100, rounded to one decimal place.
      - Minimum score is 0; maximum is 100.

    Args:
        resume_text -- Full plain text of the candidate's resume.
        keywords    -- Keywords derived from the job description.

    Returns:
        Tuple of (score: float, matched_keywords: list[str]).
    """
    resume_lower = resume_text.lower()
    matched = [kw for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', resume_lower)]
    score = round((len(matched) / len(keywords)) * 100, 1) if keywords else 0.0
    return score, matched


class RankRequest(BaseModel):
    """Request body for POST /rank."""
    job_id: int  # ID of the job to rank candidates against


class RankedCandidate(BaseModel):
    """A single ranked candidate entry returned by POST /rank."""
    id: int
    name: Optional[str]
    email: Optional[str]
    score: float           # 0–100 keyword match score
    reason: str            # Human-readable explanation listing matched keywords


@app.post("/rank", status_code=200)
def rank_candidates(payload: RankRequest, db: Session = Depends(get_db)):
    """
    Score and rank all candidates against a specific job description.

    Steps:
      1. Load the Job record; return 404 if not found.
      2. Load all Candidate rows; return 400 if none exist.
      3. Extract keywords from job.jd_text.
      4. For each candidate, count keyword matches in resume_text and compute a 0–100 score.
      5. Persist the updated score back to the database.
      6. Return candidates sorted by score descending, each with a reason string.

    Returns:
        List of RankedCandidate objects sorted highest score first.
    """
    # Step 1 — load job or 404
    job = db.get(Job, payload.job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {payload.job_id} not found")

    # Step 2 — load all candidates
    candidates = db.query(Candidate).all()
    if not candidates:
        raise HTTPException(status_code=400, detail="No candidates in database to rank")

    # Step 3 — extract keywords from the job description
    keywords = _extract_keywords(job.jd_text)
    if not keywords:
        raise HTTPException(status_code=400, detail="Could not extract keywords from job description")

    results: list[RankedCandidate] = []

    for candidate in candidates:
        # Step 4 — score the resume
        score, matched = _score_resume(candidate.resume_text, keywords)

        # Step 5 — persist updated score
        candidate.score = score
        db.add(candidate)

        # Build a human-readable reason string
        if matched:
            reason = f"Matched {len(matched)} keyword(s): {', '.join(matched[:10])}"
            if len(matched) > 10:
                reason += f" (+{len(matched) - 10} more)"
        else:
            reason = "No keywords from the job description found in resume"

        results.append(RankedCandidate(
            id=candidate.id,
            name=candidate.name,
            email=candidate.email,
            score=score,
            reason=reason,
        ))

    # Commit all score updates in a single transaction
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save scores")

    # Step 6 — return sorted by score descending
    results.sort(key=lambda c: c.score, reverse=True)
    return results


# ---------------------------------------------------------------------------
# Outreach email templates
# ---------------------------------------------------------------------------

# Subject line template.
# Placeholders: {role} — job title.
_OUTREACH_SUBJECT = "Exciting {role} Opportunity — Would Love to Connect"

# Body template for a candidate whose name was successfully inferred.
# Placeholders: {name}, {role}, {highlights}.
_OUTREACH_BODY_NAMED = """\
Hi {name},

I hope this message finds you well. My name is [Your Name], and I'm a recruiter \
working to find exceptional talent for the {role} role at [Company Name].

Having reviewed your background, I believe your experience aligns well with what \
we're looking for. In particular, I noticed {highlights}.

This is a full-time position offering a collaborative environment, competitive \
compensation, and real ownership of meaningful work.

If you're open to a brief conversation, I'd love to share more details about the \
role and learn more about your career goals.

Looking forward to hearing from you.

Best regards,
[Your Name]
[Your Title] | [Company Name]
[Your Email] | [Your Phone]
"""

# Fallback body template when no candidate name is available.
# Placeholders: {role}, {highlights}.
_OUTREACH_BODY_ANONYMOUS = """\
Hello,

I hope this message finds you well. My name is [Your Name], and I'm a recruiter \
working to find exceptional talent for the {role} role at [Company Name].

Based on your background, I believe you could be a strong fit for this opportunity. \
In particular, I noticed {highlights}.

This is a full-time position offering a collaborative environment, competitive \
compensation, and real ownership of meaningful work.

If you're open to a brief conversation, I'd love to share more details about the \
role and learn more about your career goals.

Looking forward to hearing from you.

Best regards,
[Your Name]
[Your Title] | [Company Name]
[Your Email] | [Your Phone]
"""


def _build_highlights(candidate: Candidate, job: Job) -> str:
    """
    Produce a short, natural-language highlights phrase for the outreach email.

    If the candidate has been scored, mention the top matched keywords from the
    job description so the email feels personalised. Falls back to a generic
    phrase when no scoring data is available.
    """
    # Re-use the existing keyword extractor to find what the JD cares about
    keywords = _extract_keywords(job.jd_text, top_n=10)
    if keywords and candidate.resume_text:
        resume_lower = candidate.resume_text.lower()
        matched = [
            kw for kw in keywords
            if re.search(r'\b' + re.escape(kw) + r'\b', resume_lower)
        ]
        if matched:
            top = matched[:3]
            phrase = ", ".join(top)
            return f"your experience with {phrase}"
    return "your professional background and accomplishments"


class OutreachRequest(BaseModel):
    """Request body for POST /outreach."""
    candidate_id: int  # ID of the candidate to contact
    job_id: int        # ID of the job to reference in the email


class OutreachResponse(BaseModel):
    """Response body containing the generated outreach email."""
    subject: str  # Email subject line
    body: str     # Full email body, ready to send


@app.post("/outreach", response_model=OutreachResponse, status_code=200)
def generate_outreach(payload: OutreachRequest, db: Session = Depends(get_db)):
    """
    Generate a personalised recruiter outreach email for a candidate.

    Steps:
      1. Load Candidate and Job from the database; 404 if either is missing.
      2. Build a highlights phrase from keyword matches (if resume text exists).
      3. Fill in the appropriate subject and body template.

    Returns:
        OutreachResponse with subject and body strings.
    """
    # Step 1 — load records
    candidate = db.get(Candidate, payload.candidate_id)
    if not candidate:
        raise HTTPException(
            status_code=404,
            detail=f"Candidate {payload.candidate_id} not found",
        )

    job = db.get(Job, payload.job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job {payload.job_id} not found",
        )

    # Step 2 — build the personalised highlights phrase
    highlights = _build_highlights(candidate, job)

    # Step 3 — render subject and body from the appropriate template
    subject = _OUTREACH_SUBJECT.format(role=job.title)

    if candidate.name:
        body = _OUTREACH_BODY_NAMED.format(
            name=candidate.name,
            role=job.title,
            highlights=highlights,
        )
    else:
        body = _OUTREACH_BODY_ANONYMOUS.format(
            role=job.title,
            highlights=highlights,
        )

    return OutreachResponse(subject=subject, body=body.strip())


# ---------------------------------------------------------------------------
# Copilot chat
# ---------------------------------------------------------------------------

# Intent labels used internally to route the message.
_INTENT_CREATE_JOB = "create_job"
_INTENT_RANK       = "rank_candidates"
_INTENT_OUTREACH   = "generate_outreach"
_INTENT_STATUS     = "status"
_INTENT_UNKNOWN    = "unknown"


def _detect_intent(message: str) -> str:
    """
    Classify a natural language message into one of the supported intents.

    Uses keyword matching only — no external NLP or model calls.
    Order matters: more specific patterns are checked first.
    """
    msg = message.lower()
    if any(kw in msg for kw in ["create job", "new job", "add job", "post job", "create a job"]):
        return _INTENT_CREATE_JOB
    if any(kw in msg for kw in ["rank", "score candidates", "best candidate", "top candidate"]):
        return _INTENT_RANK
    if any(kw in msg for kw in ["outreach", "email", "contact", "reach out", "message candidate"]):
        return _INTENT_OUTREACH
    if any(kw in msg for kw in ["status", "how many", "overview", "summary", "list", "show"]):
        return _INTENT_STATUS
    return _INTENT_UNKNOWN


def _extract_id(label: str, text: str) -> Optional[int]:
    """
    Extract an integer ID that follows a label word in the message.

    Handles formats like: "job 3", "job id 3", "job: 3", "job #3".
    Returns None if no matching ID is found.
    """
    match = re.search(rf'{label}\s*(?:id\s*)?[:#]?\s*(\d+)', text, re.IGNORECASE)
    return int(match.group(1)) if match else None


class ChatRequest(BaseModel):
    """Request body for POST /copilot/chat."""
    message: str              # Natural language message from the user
    session_id: str = "default"  # Identifies the conversation for memory continuity


class ChatResponse(BaseModel):
    """Response body for POST /copilot/chat."""
    reply: str  # Natural language response


@app.post("/copilot/chat", status_code=200)
async def copilot_chat(payload: ChatRequest, db: Session = Depends(get_db)):
    """
    Natural language interface to the AI Hiring Harness.

    Returns a text/event-stream (SSE) response so the client receives
    progress updates and generated text in real time instead of waiting
    for the full Ollama response to complete.

    SSE event types:
        progress -- status update (e.g. "Scoring candidates…")
        token    -- text token to append to the assistant's message
        error    -- error message
        done     -- stream finished
    """
    return StreamingResponse(
        stream_copilot(payload.message, db, session_id=payload.session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # Disable nginx proxy buffering if present
        },
    )


@app.post("/job/create", response_model=JobResponse, status_code=201)
def create_job(payload: JobCreate, db: Session = Depends(get_db)):
    job = Job(title=payload.title, jd_text=payload.jd_text)
    try:
        db.add(job)
        db.commit()
        db.refresh(job)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save job")
    return job
