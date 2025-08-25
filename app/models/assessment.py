from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum

class AssessmentStatus(enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class AssessmentCandidateStatus(enum.Enum):
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    COMPLETED = "completed"

class Assessment(Base):
    __tablename__ = "assessments"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    instructions = Column(Text)
    total_time_minutes = Column(Integer, default=120)
    max_score = Column(Float, default=100.0)
    passing_score = Column(Float, default=60.0)
    status = Column(Enum(AssessmentStatus), default=AssessmentStatus.DRAFT)
    
    # Settings
    allow_copy_paste = Column(Boolean, default=False)
    allow_tab_switching = Column(Boolean, default=False)
    randomize_questions = Column(Boolean, default=False)
    auto_submit = Column(Boolean, default=True)
    
    # Dates
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    assessment_questions = relationship("AssessmentQuestion", back_populates="assessment", cascade="all, delete-orphan")
    assessment_candidates = relationship("AssessmentCandidate", back_populates="assessment", cascade="all, delete-orphan")

class AssessmentQuestion(Base):
    __tablename__ = "assessment_questions"
    
    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    order_index = Column(Integer, default=0)
    weight = Column(Float, default=1.0)
    time_limit_minutes = Column(Integer)  # Override question's time limit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    assessment = relationship("Assessment", back_populates="assessment_questions")
    question = relationship("Question", back_populates="assessment_questions")

class AssessmentCandidate(Base):
    __tablename__ = "assessment_candidates"
    
    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    status = Column(Enum(AssessmentCandidateStatus), default=AssessmentCandidateStatus.ASSIGNED)
    
    # Tracking
    started_at = Column(DateTime(timezone=True))
    submitted_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    total_time_spent_minutes = Column(Integer, default=0)
    
    # Scoring
    total_score = Column(Float, default=0.0)
    percentage_score = Column(Float, default=0.0)
    questions_attempted = Column(Integer, default=0)
    questions_correct = Column(Integer, default=0)
    
    # Access control
    access_token = Column(String, unique=True, index=True)  # Unique token for candidate access
    access_expires_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    assessment = relationship("Assessment", back_populates="assessment_candidates")
    candidate = relationship("Candidate", back_populates="assessment_candidates")