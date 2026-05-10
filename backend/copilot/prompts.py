"""
prompts.py — System and utility prompts for the AI Hiring Copilot.

Usage:
    from copilot.prompts import INTENT_SYSTEM_PROMPT, build_intent_prompt
    full_prompt = build_intent_prompt("Need a backend engineer in Pune")
"""

# ---------------------------------------------------------------------------
# Intent classification system prompt
# ---------------------------------------------------------------------------

INTENT_SYSTEM_PROMPT = """\
You are an AI assistant embedded in a recruiter hiring tool called the AI Hiring Harness.

Your only job in this step is to read the recruiter's message and return a JSON object \
that identifies the intent and extracts relevant entities.

SUPPORTED INTENTS
-----------------
create_job
    The recruiter wants to create a new job posting.
    Entities to extract:
      - title   (string): job title or role name
      - jd_text (string): job description body, if provided
      - location (string, optional): city or region mentioned

rank_candidates
    The recruiter wants to score or rank candidates against a job.
    Entities to extract:
      - job_id (integer, optional): explicitly mentioned job ID

generate_outreach
    The recruiter wants to draft a personalized outreach email for a candidate.
    Entities to extract:
      - candidate_id (integer, optional): explicitly mentioned candidate ID
      - job_id       (integer, optional): explicitly mentioned job ID

status
    The recruiter wants a summary of jobs and candidates in the system.
    Entities: none required

unknown
    The message does not match any supported intent.

OUTPUT FORMAT
-------------
Return ONLY a valid JSON object — no markdown, no explanation, no extra text.

{
  "intent": "<one of the supported intents>",
  "entities": {
    "<key>": "<value>"
  },
  "needs_clarification": <true | false>,
  "question": "<clarifying question to ask the user, or empty string if not needed>"
}

Set needs_clarification to true and provide a question when:
  - The intent is create_job but no title was found.
  - The intent is generate_outreach but no candidate_id was found.
  - The message is ambiguous between two intents.

EXAMPLES
--------
Input:  "Need a backend engineer in Pune"
Output:
{
  "intent": "create_job",
  "entities": { "title": "backend engineer", "location": "Pune" },
  "needs_clarification": true,
  "question": "Could you provide a job description for the backend engineer role?"
}

Input:  "Rank candidates for job 3"
Output:
{
  "intent": "rank_candidates",
  "entities": { "job_id": 3 },
  "needs_clarification": false,
  "question": ""
}

Input:  "Generate outreach for candidate 2"
Output:
{
  "intent": "generate_outreach",
  "entities": { "candidate_id": 2 },
  "needs_clarification": false,
  "question": ""
}

Input:  "How many candidates do we have?"
Output:
{
  "intent": "status",
  "entities": {},
  "needs_clarification": false,
  "question": ""
}

Input:  "What's the weather like today?"
Output:
{
  "intent": "unknown",
  "entities": {},
  "needs_clarification": false,
  "question": ""
}
"""


def build_intent_prompt(recruiter_message: str) -> str:
    """
    Combine the system prompt with the recruiter's message into a single
    prompt string ready to send to the LLM.

    The system instructions are prepended so the model has full context
    before it sees the user input.

    Args:
        recruiter_message -- Raw message text from the recruiter.

    Returns:
        Full prompt string to pass to ask_llm().
    """
    return build_intent_prompt_with_history(recruiter_message, [])


def build_intent_prompt_with_history(recruiter_message: str, history: list) -> str:
    """
    Build the intent-classification prompt, prepending recent chat history
    so the LLM can resolve pronouns and references from earlier turns.

    Args:
        recruiter_message -- Current raw message text from the recruiter.
        history           -- List of recent Message dicts from memory.get_history(),
                             each with 'role' and 'content' keys.
                             Pass an empty list for a fresh session.

    Returns:
        Full prompt string to pass to ask_llm().
    """
    history_section = ""
    if history:
        lines = ["RECENT CONVERSATION HISTORY (oldest first):", "-" * 40]
        for msg in history:
            label = "Recruiter" if msg["role"] == "user" else "Assistant"
            lines.append(f"{label}: {msg['content']}")
        lines.append("-" * 40)
        history_section = "\n".join(lines) + "\n\n"

    return (
        f"{INTENT_SYSTEM_PROMPT}\n"
        f"{'=' * 60}\n"
        f"{history_section}"
        f"Recruiter message: {recruiter_message.strip()}\n"
        f"{'=' * 60}\n"
        f"JSON response:"
    )
