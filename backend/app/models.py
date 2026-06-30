import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Date, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
from app.database import Base

def utcnow():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

class PriorityEnum(str, enum.Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    URGENT = "Urgent"

class StatusEnum(str, enum.Enum):
    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    OVERDUE = "Overdue"

class HabitFrequencyEnum(str, enum.Enum):
    DAILY = "Daily"
    WEEKLY = "Weekly"

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    due_date = Column(DateTime, nullable=False)
    priority = Column(SQLEnum(PriorityEnum), default=PriorityEnum.MEDIUM)
    status = Column(SQLEnum(StatusEnum), default=StatusEnum.PENDING)
    estimated_hours = Column(Float, default=1.0)
    category = Column(String, default="Work")
    panic_index = Column(Float, default=0.0)
    created_at = Column(DateTime, default=utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Explainable AI & Rescue Columns
    impact = Column(String, default="Medium")
    reward = Column(String, nullable=True)
    loss_if_skipped = Column(String, nullable=True)
    completion_probability = Column(Float, default=1.0)
    rescue_strategy = Column(String, nullable=True)
    critical_next_action = Column(String, nullable=True)
    ai_reasoning = Column(String, nullable=True)
    rescue_timeline = Column(String, default="[]")  # JSON encoded list of timeline slots
    actual_hours_spent = Column(Float, default=0.0)

    # Relationships
    subtasks = relationship("SubTask", back_populates="task", cascade="all, delete-orphan", lazy="joined")
    schedule_blocks = relationship("ScheduleBlock", back_populates="task", cascade="all, delete-orphan", lazy="joined")
    email_drafts = relationship("EmailDraft", back_populates="task", cascade="all, delete-orphan")

class SubTask(Base):
    __tablename__ = "subtasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    is_completed = Column(Boolean, default=False)
    estimated_minutes = Column(Integer, default=30)
    order = Column(Integer, default=0)

    # Relationships
    task = relationship("Task", back_populates="subtasks")

class ScheduleBlock(Base):
    __tablename__ = "schedule_blocks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    is_focus_block = Column(Boolean, default=False)

    # Relationships
    task = relationship("Task", back_populates="schedule_blocks")

class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    source = Column(String, default="Google Calendar")
    is_external = Column(Boolean, default=True)

class EmailDraft(Base):
    __tablename__ = "email_drafts"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    recipient = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    body = Column(String, nullable=False)
    status = Column(String, default="Draft")
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    task = relationship("Task", back_populates="email_drafts")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    message = Column(String, nullable=False)
    type = Column(String, default="info")  # "urgent", "warning", "info"
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)

class AIMemory(Base):
    __tablename__ = "ai_memory"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, nullable=False)  # "procrastination", "efficiency", "preferences"
    pattern_key = Column(String, unique=True, index=True, nullable=False)
    pattern_data = Column(String, default="{}")  # JSON string of pattern parameters
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

class AgentActivity(Base):
    __tablename__ = "agent_activity"

    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String, nullable=False)
    action_taken = Column(String, nullable=False)
    timestamp = Column(DateTime, default=utcnow)

class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    sleep_hours = Column(Float, default=8.0)
    meeting_load_hours = Column(Float, default=2.0)
    daily_focus_target = Column(Float, default=4.0)
    google_account_connected = Column(Boolean, default=False)
    google_refresh_token_id = Column(String, nullable=True)
    start_work_hour = Column(Integer, default=9)
    end_work_hour = Column(Integer, default=18)

class RiskEngineConfig(Base):
    __tablename__ = "risk_engine_config"

    id = Column(Integer, primary_key=True, index=True)
    threshold_warning = Column(Float, default=0.70)
    threshold_critical = Column(Float, default=0.40)
    prediction_window_hours = Column(Integer, default=48)

class Habit(Base):
    __tablename__ = "habits"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    frequency = Column(SQLEnum(HabitFrequencyEnum), default=HabitFrequencyEnum.DAILY)
    streak = Column(Integer, default=0)
    last_completed_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    logs = relationship("HabitLog", back_populates="habit", cascade="all, delete-orphan")

class HabitLog(Base):
    __tablename__ = "habit_logs"

    id = Column(Integer, primary_key=True, index=True)
    habit_id = Column(Integer, ForeignKey("habits.id", ondelete="CASCADE"), nullable=False)
    completed_date = Column(Date, nullable=False)

    # Relationships
    habit = relationship("Habit", back_populates="logs")

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String, nullable=False)
    category = Column(String, default="General")
    created_at = Column(DateTime, default=utcnow)
    dismissed = Column(Boolean, default=False)
