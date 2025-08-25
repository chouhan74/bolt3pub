from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum

class SubmissionStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"

class VerdictType(enum.Enum):
    OK = "OK"  # Accepted
    WA = "WA"  # Wrong Answer
    TLE = "TLE"  # Time Limit Exceeded
    MLE = "MLE"  # Memory Limit Exceeded
    RTE = "RTE"  # Runtime Error
    CE = "CE"  # Compilation Error

class Submission(Base):
    __tablename__ = "submissions"
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    assessment_id = Column(Integer, ForeignKey("assessments.id"))
    
    # Submission details
    code = Column(Text, nullable=False)
    language = Column(String, nullable=False)
    is_final_submission = Column(Boolean, default=False)
    
    # Execution results
    status = Column(Enum(SubmissionStatus), default=SubmissionStatus.PENDING)
    overall_verdict = Column(Enum(VerdictType))
    total_score = Column(Float, default=0.0)
    execution_time_ms = Column(Integer, default=0)
    memory_used_kb = Column(Integer, default=0)
    
    # Error details
    compilation_error = Column(Text)
    runtime_error = Column(Text)
    
    # Metadata
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    executed_at = Column(DateTime(timezone=True))
    
    # Relationships
    candidate = relationship("Candidate", back_populates="submissions")
    results = relationship("SubmissionResult", back_populates="submission", cascade="all, delete-orphan")

class SubmissionResult(Base):
    __tablename__ = "submission_results"
    
    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)
    test_case_id = Column(Integer, ForeignKey("test_cases.id"), nullable=False)
    
    # Test case execution results
    verdict = Column(Enum(VerdictType), nullable=False)
    execution_time_ms = Column(Integer, default=0)
    memory_used_kb = Column(Integer, default=0)
    score = Column(Float, default=0.0)
    
    # Output comparison
    actual_output = Column(Text)
    error_message = Column(Text)
    
    executed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    submission = relationship("Submission", back_populates="results")