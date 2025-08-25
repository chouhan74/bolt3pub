from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Candidate(Base):
    __tablename__ = "candidates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String)
    position = Column(String)
    experience_years = Column(Integer, default=0)
    skills = Column(Text)  # JSON string of skills
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    assessment_candidates = relationship("AssessmentCandidate", back_populates="candidate")
    submissions = relationship("Submission", back_populates="candidate")
    proctoring_events = relationship("ProctoringEvent", back_populates="candidate")