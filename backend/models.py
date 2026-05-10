from sqlalchemy import Column, Integer, String, DateTime, Float
from datetime import datetime, timezone
from db import Base


class Candidate(Base):
    """
    Represents a job candidate whose resume has been uploaded.

    Fields:
        id          -- Auto-incrementing primary key.
        name        -- Inferred from the first lines of the resume; may be None.
        email       -- Extracted via regex from resume text; may be None.
        resume_text -- Full plain text extracted from the uploaded PDF.
        resume_path -- Relative path to the saved PDF file under uploads/; may be None.
        score       -- AI-assigned relevance score (populated later); None until scored.
        created_at  -- UTC timestamp set automatically when the record is inserted.
    """
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)          # Inferred heuristically; not always reliable
    email = Column(String, nullable=True)         # Extracted via regex
    resume_text = Column(String, nullable=False)  # Raw text from all PDF pages joined
    resume_path = Column(String, nullable=True)   # Relative path to stored PDF, e.g. uploads/<uuid>.pdf
    score = Column(Float, nullable=True)          # Reserved for AI scoring step
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Job(Base):
    """
    Represents a job posting created by a recruiter.

    Fields:
        id         -- Auto-incrementing primary key.
        title      -- Job title (e.g. "Senior Backend Engineer").
        jd_text    -- Full job description text used for AI matching.
        created_at -- UTC timestamp set automatically when the record is inserted.
    """
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)    # Short label for the role
    jd_text = Column(String, nullable=False)  # Full JD used as context for scoring
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
