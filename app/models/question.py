from sqlalchemy import Column, Integer, String, Text, Enum, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum

class QuestionType(enum.Enum):
    MCQ = "mcq"
    CODING = "coding"

class DifficultyLevel(enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class Question(Base):
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    question_type = Column(Enum(QuestionType), nullable=False)
    difficulty = Column(Enum(DifficultyLevel), default=DifficultyLevel.MEDIUM)
    tags = Column(Text)  # JSON string of tags
    max_score = Column(Float, default=100.0)
    time_limit_minutes = Column(Integer, default=30)
    
    # For coding questions
    template_code = Column(Text)  # Starter code template
    solution_code = Column(Text)  # Reference solution
    allowed_languages = Column(Text)  # JSON string of allowed languages
    
    # For MCQ questions
    options = Column(Text)  # JSON string of options
    correct_answer = Column(String)  # For MCQ questions
    
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    test_cases = relationship("TestCase", back_populates="question", cascade="all, delete-orphan")
    assessment_questions = relationship("AssessmentQuestion", back_populates="question")

class TestCase(Base):
    __tablename__ = "test_cases"
    
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    input_data = Column(Text, nullable=False)
    expected_output = Column(Text, nullable=False)
    is_public = Column(Boolean, default=True, nullable=False)  # Public test cases shown to candidate
    weight = Column(Float, default=1.0)  # Weight for scoring
    time_limit_seconds = Column(Integer, default=5)
    memory_limit_mb = Column(Integer, default=128)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    question = relationship("Question", back_populates="test_cases")