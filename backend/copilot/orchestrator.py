"""
orchestrator.py — Core logic that ties the LLM, prompts, and tools together.

Exposes two async entry points:
    run_copilot(message, db, session_id)   -> str
        Awaits the full reply. Used by callers that need a complete string.

    stream_copilot(message, db, session_id) -> AsyncGenerator[str, None]
        Yields SSE-formatted strings so the client sees progress and text
        in real time instead of waiting for the full generation to finish.
        Event format (newline-delimited JSON wrapped in SSE):
            data: {"type": "progress", "text": "..."}  -- status update
            data: {"type": "token",    "text": "..."}  -- text token
            data: {"type": "error",    "text": "..."}  -- error message
            data: {"type": "done"}                     -- stream finished

Flow:
    1. Load recent chat history for the session from memory.
    2. Build intent-classification prompt (with history for context).
    3. Send prompt to local LLM via ask_llm() — async, non-blocking.
    4. Safely parse the JSON response.
    5. If the LLM wants clarification (and NOT resuming a pending turn),
       save intent+entities and return/yield the question.
    6. If we have saved pending state (user just answered a question), restore
       and merge so we never loop back to step 5 for the same request.
    7. Dispatch to the appropriate async tool.
    8. Convert the tool result into a recruiter-friendly reply string.
       For generate_outreach in stream_copilot, stream tokens in real time.
    9. Persist both turns (user + assistant) to session memory.
"""

import json
import re
from collections.abc import AsyncGenerator

from copilot.llm import ask_llm, stream_llm
from copilot.memory import add_message, get_history
from copilot.prompts import build_intent_prompt_with_history
from copilot.tools import (
    build_outreach_plaintext_prompt,
    create_job_tool,
    generate_outreach_tool,
    rank_candidates_tool,
    status_tool,
)

# ---------------------------------------------------------------------------
# Pending-state store — maps session_id → {intent, entities}
# Populated when a clarifying question is returned; consumed on the next turn.
# ---------------------------------------------------------------------------
_pending: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# JSON extraction helper
# ---------------------------------------------------------------------------

def _parse_llm_json(raw: str) -> dict | None:
    text = raw.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None


# ---------------------------------------------------------------------------
# Response formatters
# ---------------------------------------------------------------------------

def _format_create_job(result: dict) -> str:
    if not result["ok"]:
        return f"I couldn't create the job: {result['error']}"
    job = result["job"]
    return (
        f"Job created successfully!\n"
        f"  ID: {job['id']}\n"
        f"  Title: \"{job['title']}\"\n"
        f"  Created at: {job['created_at']}"
    )


def _format_rank(result: dict) -> str:
    if not result["ok"]:
        return f"Ranking failed: {result['error']}"
    job = result["job"]
    candidates = result["candidates"]
    if not candidates:
        return f"No candidates to rank for \"{job['title']}\"."
    lines = [f"Ranked {len(candidates)} candidate(s) against \"{job['title']}\":\n"]
    for i, c in enumerate(candidates, 1):
        name = c["name"] or f"Candidate #{c['id']}"
        explanation = c.get("explanation", "No explanation available.")
        lines.append(f"  {i}. {name} — {c['score']}/100")
        lines.append(f"     {explanation}")
    return "\n".join(lines)


def _format_outreach(result: dict) -> str:
    if not result["ok"]:
        return f"Outreach generation failed: {result['error']}"
    return (
        f"Here's your outreach email:\n\n"
        f"Subject: {result['subject']}\n\n"
        f"{result['body']}"
    )


def _format_status(result: dict) -> str:
    if not result["ok"]:
        return f"Could not retrieve status: {result['error']}"
    lines = [
        "Here's the current status of your hiring harness:\n",
        f"  • Jobs:       {result['jobs']}",
        f"  • Candidates: {result['candidates']} ({result['scored_candidates']} scored)",
    ]
    if result["recent_jobs"]:
        lines.append("\nRecent jobs:")
        for job in result["recent_jobs"]:
            lines.append(f"  [{job['id']}] {job['title']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

async def run_copilot(message: str, db=None, session_id: str = "default") -> str:  # noqa: ARG001
    """Async: process a recruiter message end-to-end and return a reply string."""
    history = get_history(session_id)
    prompt = build_intent_prompt_with_history(message, history)

    try:
        # num_predict=300: intent JSON is small; capping tokens avoids the
        # model rambling past the closing brace on slow CPU hardware.
        raw_response = await ask_llm(prompt, num_predict=300)
    except RuntimeError as exc:
        return (
            f"I'm having trouble connecting to the AI model right now.\n"
            f"Details: {exc}\n\n"
            f"You can still use the API endpoints directly while Ollama is unavailable."
        )

    parsed = _parse_llm_json(raw_response)
    if parsed is None:
        return (
            "I received an unexpected response from the AI model and couldn't parse it. "
            "Please try rephrasing your message."
        )

    intent = parsed.get("intent", "unknown")
    entities = parsed.get("entities", {})
    needs_clarification = parsed.get("needs_clarification", False)
    question = parsed.get("question", "").strip()

    # --- Restore pending state if the user is answering a previous question ---
    pending = _pending.pop(session_id, None)
    if pending:
        # Use stored intent when LLM couldn't figure it out from the short answer
        if not intent or intent == "unknown":
            intent = pending["intent"]
        # Merge: stored values as base, new LLM entities override where present
        merged = dict(pending["entities"])
        for k, v in entities.items():
            if v:
                merged[k] = v
        # Treat the raw message as the answer to whatever was missing
        if intent == "create_job":
            if not merged.get("jd_text"):
                merged["jd_text"] = message
            if not merged.get("title") and pending["entities"].get("title"):
                merged["title"] = pending["entities"]["title"]
        entities = merged
        needs_clarification = False  # never loop on a direct answer

    # --- Ask for clarification only on the first missing-info turn ---
    if needs_clarification and question:
        _pending[session_id] = {"intent": intent, "entities": entities}
        add_message(session_id, "user", message)
        add_message(session_id, "assistant", question)
        return question

    # --- Dispatch ---
    if intent == "create_job":
        title = entities.get("title", "").strip()
        jd_text = entities.get("jd_text", "").strip()

        # Try to recover title from earlier user messages
        if not title:
            for msg in reversed(history):
                if msg["role"] == "user":
                    m = re.search(
                        r'(\w+\s+(?:engineer|developer|designer|manager|analyst|scientist|lead|architect))',
                        msg["content"], re.IGNORECASE,
                    )
                    if m:
                        title = m.group(1).strip()
                        break

        if not title:
            reply = "What job title would you like to create? Please include a title and description."
        elif not jd_text:
            reply = (
                f"I found the title \"{title}\" but need a job description. "
                f"Describe the role briefly (required skills, experience, responsibilities)."
            )
        else:
            reply = _format_create_job(create_job_tool(title, jd_text))

    elif intent == "rank_candidates":
        raw_id = entities.get("job_id")
        try:
            job_id = int(raw_id) if raw_id is not None else None
        except (ValueError, TypeError):
            job_id = None
        if job_id is None:
            from db import SessionLocal
            from models import Job
            db_session = SessionLocal()
            try:
                latest = db_session.query(Job).order_by(Job.id.desc()).first()
            finally:
                db_session.close()
            if not latest:
                reply = "There are no jobs in the system yet. Create a job first."
            else:
                job_id = latest.id
                prefix = f"No job ID specified — using the most recent job: \"{latest.title}\" (ID {job_id}).\n\n"
                reply = prefix + _format_rank(await rank_candidates_tool(job_id))
        else:
            reply = _format_rank(await rank_candidates_tool(job_id))

    elif intent == "generate_outreach":
        raw_cid = entities.get("candidate_id")
        raw_jid = entities.get("job_id")
        try:
            candidate_id = int(raw_cid) if raw_cid is not None else None
        except (ValueError, TypeError):
            candidate_id = None
        try:
            job_id = int(raw_jid) if raw_jid is not None else None
        except (ValueError, TypeError):
            job_id = None
        if candidate_id is None:
            reply = "Which candidate would you like to contact? Please provide a candidate ID."
        else:
            if job_id is None:
                from db import SessionLocal
                from models import Job
                db_session = SessionLocal()
                try:
                    latest = db_session.query(Job).order_by(Job.id.desc()).first()
                finally:
                    db_session.close()
                if not latest:
                    reply = "There are no jobs in the system yet. Create a job first."
                else:
                    job_id = latest.id
                    reply = _format_outreach(await generate_outreach_tool(candidate_id, job_id))
            else:
                reply = _format_outreach(await generate_outreach_tool(candidate_id, job_id))

    elif intent == "status":
        reply = _format_status(status_tool())

    else:
        reply = (
            "I'm not sure what you'd like to do. Here's what I can help with:\n"
            "  \u2022 \"Create a job titled '...' description: ...\"\n"
            "  \u2022 \"Rank candidates for job 1\"\n"
            "  \u2022 \"Generate outreach for candidate 2\"\n"
            "  \u2022 \"Show status\""
        )

    add_message(session_id, "user", message)
    add_message(session_id, "assistant", reply)
    return reply


# ---------------------------------------------------------------------------
# Streaming entry point
# ---------------------------------------------------------------------------

async def stream_copilot(
    message: str, db=None, session_id: str = "default"  # noqa: ARG001
) -> AsyncGenerator[str, None]:
    """
    Async generator that processes a recruiter message and yields SSE strings.

    Progress events are emitted immediately so the client always sees activity.
    For generate_outreach the email is streamed token-by-token directly from
    Ollama using stream_llm(), giving a real-time typing effect.
    All other intents send a complete formatted reply once tools finish.
    """

    def _sse(data: dict) -> str:
        return f"data: {json.dumps(data)}\n\n"

    # --- Immediately signal that we're thinking ---
    yield _sse({"type": "progress", "text": "Analysing your request\u2026"})

    history = get_history(session_id)
    prompt = build_intent_prompt_with_history(message, history)

    try:
        raw_response = await ask_llm(prompt, num_predict=300)
    except RuntimeError as exc:
        err = (
            "I'm having trouble connecting to the AI model right now.\n"
            f"Details: {exc}\n\n"
            "You can still use the API endpoints directly while Ollama is unavailable."
        )
        add_message(session_id, "user", message)
        add_message(session_id, "assistant", err)
        yield _sse({"type": "token", "text": err})
        yield _sse({"type": "done"})
        return

    parsed = _parse_llm_json(raw_response)
    if parsed is None:
        err = (
            "I received an unexpected response from the AI model and couldn't parse it. "
            "Please try rephrasing your message."
        )
        yield _sse({"type": "token", "text": err})
        yield _sse({"type": "done"})
        return

    intent = parsed.get("intent", "unknown")
    entities = parsed.get("entities", {})
    needs_clarification = parsed.get("needs_clarification", False)
    question = parsed.get("question", "").strip()

    pending = _pending.pop(session_id, None)
    if pending:
        if not intent or intent == "unknown":
            intent = pending["intent"]
        merged = dict(pending["entities"])
        for k, v in entities.items():
            if v:
                merged[k] = v
        if intent == "create_job":
            if not merged.get("jd_text"):
                merged["jd_text"] = message
            if not merged.get("title") and pending["entities"].get("title"):
                merged["title"] = pending["entities"]["title"]
        entities = merged
        needs_clarification = False

    if needs_clarification and question:
        _pending[session_id] = {"intent": intent, "entities": entities}
        add_message(session_id, "user", message)
        add_message(session_id, "assistant", question)
        yield _sse({"type": "token", "text": question})
        yield _sse({"type": "done"})
        return

    # --- Dispatch ---
    reply = ""

    if intent == "create_job":
        title = entities.get("title", "").strip()
        jd_text = entities.get("jd_text", "").strip()

        if not title:
            for msg in reversed(history):
                if msg["role"] == "user":
                    m = re.search(
                        r'(\w+\s+(?:engineer|developer|designer|manager|analyst|scientist|lead|architect))',
                        msg["content"], re.IGNORECASE,
                    )
                    if m:
                        title = m.group(1).strip()
                        break

        if not title:
            reply = "What job title would you like to create? Please include a title and description."
        elif not jd_text:
            reply = (
                f"I found the title \"{title}\" but need a job description. "
                f"Describe the role briefly (required skills, experience, responsibilities)."
            )
        else:
            reply = _format_create_job(create_job_tool(title, jd_text))
        yield _sse({"type": "token", "text": reply})

    elif intent == "rank_candidates":
        yield _sse({"type": "progress", "text": "Scoring candidates against the job description\u2026"})
        raw_id = entities.get("job_id")
        try:
            job_id = int(raw_id) if raw_id is not None else None
        except (ValueError, TypeError):
            job_id = None
        if job_id is None:
            from db import SessionLocal
            from models import Job
            db_session = SessionLocal()
            try:
                latest = db_session.query(Job).order_by(Job.id.desc()).first()
            finally:
                db_session.close()
            if not latest:
                reply = "There are no jobs in the system yet. Create a job first."
            else:
                job_id = latest.id
                prefix = f"No job ID specified \u2014 using the most recent job: \"{latest.title}\" (ID {job_id}).\n\n"
                reply = prefix + _format_rank(await rank_candidates_tool(job_id))
        else:
            reply = _format_rank(await rank_candidates_tool(job_id))
        yield _sse({"type": "token", "text": reply})

    elif intent == "generate_outreach":
        raw_cid = entities.get("candidate_id")
        raw_jid = entities.get("job_id")
        try:
            candidate_id = int(raw_cid) if raw_cid is not None else None
        except (ValueError, TypeError):
            candidate_id = None
        try:
            job_id = int(raw_jid) if raw_jid is not None else None
        except (ValueError, TypeError):
            job_id = None

        if candidate_id is None:
            reply = "Which candidate would you like to contact? Please provide a candidate ID."
            yield _sse({"type": "token", "text": reply})
        else:
            # Resolve job_id if not specified
            if job_id is None:
                from db import SessionLocal
                from models import Job
                db_session = SessionLocal()
                try:
                    latest = db_session.query(Job).order_by(Job.id.desc()).first()
                finally:
                    db_session.close()
                if not latest:
                    reply = "There are no jobs in the system yet. Create a job first."
                    yield _sse({"type": "token", "text": reply})
                    add_message(session_id, "user", message)
                    add_message(session_id, "assistant", reply)
                    yield _sse({"type": "done"})
                    return
                job_id = latest.id

            # Load candidate + job data for streaming prompt
            from db import SessionLocal
            from models import Candidate, Job
            db_session = SessionLocal()
            try:
                cand = db_session.get(Candidate, candidate_id)
                job = db_session.get(Job, job_id)
                if not cand:
                    reply = f"Candidate {candidate_id} not found."
                    yield _sse({"type": "token", "text": reply})
                    add_message(session_id, "user", message)
                    add_message(session_id, "assistant", reply)
                    yield _sse({"type": "done"})
                    return
                if not job:
                    reply = f"Job {job_id} not found."
                    yield _sse({"type": "token", "text": reply})
                    add_message(session_id, "user", message)
                    add_message(session_id, "assistant", reply)
                    yield _sse({"type": "done"})
                    return
                outreach_prompt = build_outreach_plaintext_prompt(
                    candidate_name=cand.name,
                    candidate_email=cand.email,
                    resume_text=cand.resume_text,
                    job_title=job.title,
                    jd_text=job.jd_text,
                )
            finally:
                db_session.close()

            # Stream the email token-by-token directly from Ollama
            yield _sse({"type": "progress", "text": "Drafting outreach email\u2026"})
            collected: list[str] = []
            try:
                async for token in stream_llm(outreach_prompt, num_predict=512):
                    collected.append(token)
                    yield _sse({"type": "token", "text": token})
            except RuntimeError as exc:
                err = f"Error generating outreach: {exc}"
                yield _sse({"type": "error", "text": err})
                yield _sse({"type": "done"})
                return
            reply = "".join(collected)

    elif intent == "status":
        reply = _format_status(status_tool())
        yield _sse({"type": "token", "text": reply})

    else:
        reply = (
            "I'm not sure what you'd like to do. Here's what I can help with:\n"
            "  \u2022 \"Create a job titled '...' description: ...\"\n"
            "  \u2022 \"Rank candidates for job 1\"\n"
            "  \u2022 \"Generate outreach for candidate 2\"\n"
            "  \u2022 \"Show status\""
        )
        yield _sse({"type": "token", "text": reply})

    add_message(session_id, "user", message)
    add_message(session_id, "assistant", reply)
    yield _sse({"type": "done"})
