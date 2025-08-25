from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum

class ProctoringEventType(enum.Enum):
    TAB_SWITCH = "tab_switch"
    COPY_PASTE = "copy_paste"
    WINDOW_BLUR = "window_blur"
    WINDOW_FOCUS = "window_focus"
    WINDOW_RESIZE = "window_resize"
    FULLSCREEN_EXIT = "fullscreen_exit"
    RIGHT_CLICK = "right_click"
    KEY_COMBINATION = "key_combination"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"

class ProctoringEvent(Base):
    __tablename__ = "proctoring_events"
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    assessment_id = Column(Integer, ForeignKey("assessments.id"))
    
    event_type = Column(Enum(ProctoringEventType), nullable=False)
    event_data = Column(Text)  # JSON string with additional event data
    severity = Column(String, default="medium")  # low, medium, high
    is_violation = Column(Boolean, default=False)
    
    # Browser/System info
    user_agent = Column(String)
    ip_address = Column(String)
    screen_resolution = Column(String)
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    candidate = relationship("Candidate", back_populates="proctoring_events")