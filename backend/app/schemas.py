from pydantic import BaseModel, Field
from datetime import datetime, date, timezone
from typing import List, Optional
from app.models import PriorityEnum, StatusEnum, HabitFrequencyEnum

# SubTask Schemas
class SubTaskBase(BaseModel):
    title: str
    is_completed: bool = False
    estimated_minutes: int = 30
    order: int = 0

class SubTaskCreate(SubTaskBase):
    pass

class SubTask(SubTaskBase):
    id: int
    task_id: int

    class Config:
        from_attributes = True

# ScheduleBlock Schemas
class ScheduleBlockBase(BaseModel):
    start_time: datetime
    end_time: datetime
    is_focus_block: bool = False
    gcal_event_id: Optional[str] = None

class ScheduleBlockCreate(ScheduleBlockBase):
    task_id: int

class ScheduleBlock(ScheduleBlockBase):
    id: int
    task_id: int

    class Config:
        from_attributes = True

# CalendarEvent Schemas
class CalendarEventBase(BaseModel):
    title: str
    start_time: datetime
    end_time: datetime
    source: str = "Google Calendar"
    is_external: bool = True

class CalendarEventCreate(CalendarEventBase):
    pass

class CalendarEvent(CalendarEventBase):
    id: int

    class Config:
        from_attributes = True

# EmailDraft Schemas
class EmailDraftBase(BaseModel):
    recipient: str
    subject: str
    body: str
    status: str = "Draft"

class EmailDraftCreate(EmailDraftBase):
    task_id: int

class EmailDraft(EmailDraftBase):
    id: int
    task_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Notification Schemas
class NotificationBase(BaseModel):
    message: str
    type: str = "info"
    is_read: bool = False

class NotificationCreate(NotificationBase):
    pass

class Notification(NotificationBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# AIMemory Schemas
class AIMemoryBase(BaseModel):
    category: str
    pattern_key: str
    pattern_data: str = "{}"

class AIMemoryCreate(AIMemoryBase):
    pass

class AIMemory(AIMemoryBase):
    id: int
    updated_at: datetime

    class Config:
        from_attributes = True

# AgentActivity Schemas
class AgentActivityBase(BaseModel):
    agent_name: str
    action_taken: str

class AgentActivity(AgentActivityBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True

# UserSettings Schemas
class UserSettingsBase(BaseModel):
    sleep_hours: float = 8.0
    meeting_load_hours: float = 2.0
    daily_focus_target: float = 4.0
    google_account_connected: bool = False
    google_refresh_token_id: Optional[str] = None
    start_work_hour: int = 9
    end_work_hour: int = 18

class UserSettingsUpdate(BaseModel):
    sleep_hours: Optional[float] = None
    meeting_load_hours: Optional[float] = None
    daily_focus_target: Optional[float] = None
    google_account_connected: Optional[bool] = None
    google_refresh_token_id: Optional[str] = None
    start_work_hour: Optional[int] = None
    end_work_hour: Optional[int] = None

class UserSettings(UserSettingsBase):
    id: int

    class Config:
        from_attributes = True

# RiskEngineConfig Schemas
class RiskEngineConfigBase(BaseModel):
    threshold_warning: float = 0.70
    threshold_critical: float = 0.40
    prediction_window_hours: int = 48

class RiskEngineConfig(RiskEngineConfigBase):
    id: int

    class Config:
        from_attributes = True

# Task Schemas
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: datetime
    priority: Optional[PriorityEnum] = PriorityEnum.MEDIUM
    status: Optional[StatusEnum] = StatusEnum.PENDING
    estimated_hours: Optional[float] = 1.0
    category: Optional[str] = "Work"
    impact: Optional[str] = "Medium"
    reward: Optional[str] = None
    loss_if_skipped: Optional[str] = None

class TaskCreate(TaskBase):
    subtasks: Optional[List[SubTaskCreate]] = []

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Optional[PriorityEnum] = None
    status: Optional[StatusEnum] = None
    estimated_hours: Optional[float] = None
    category: Optional[str] = None
    impact: Optional[str] = None
    reward: Optional[str] = None
    loss_if_skipped: Optional[str] = None
    completion_probability: Optional[float] = None
    rescue_strategy: Optional[str] = None
    critical_next_action: Optional[str] = None
    ai_reasoning: Optional[str] = None
    rescue_timeline: Optional[str] = None
    actual_hours_spent: Optional[float] = None

class Task(TaskBase):
    id: int
    panic_index: float
    created_at: datetime
    completed_at: Optional[datetime] = None
    completion_probability: float
    rescue_strategy: Optional[str] = None
    critical_next_action: Optional[str] = None
    ai_reasoning: Optional[str] = None
    rescue_timeline: Optional[str] = "[]"
    actual_hours_spent: float
    subtasks: List[SubTask] = []
    schedule_blocks: List[ScheduleBlock] = []

    class Config:
        from_attributes = True

# Habit Schemas
class HabitLogBase(BaseModel):
    completed_date: date

class HabitLogCreate(HabitLogBase):
    habit_id: Optional[int] = None

class HabitLog(HabitLogBase):
    id: int
    habit_id: int

    class Config:
        from_attributes = True

class HabitBase(BaseModel):
    title: str
    frequency: HabitFrequencyEnum = HabitFrequencyEnum.DAILY

class HabitCreate(HabitBase):
    pass

class Habit(HabitBase):
    id: int
    streak: int
    last_completed_date: Optional[date] = None
    created_at: datetime
    logs: List[HabitLog] = []

    class Config:
        from_attributes = True

# Recommendation Schemas
class RecommendationBase(BaseModel):
    content: str
    category: str = "General"

class Recommendation(RecommendationBase):
    id: int
    created_at: datetime
    dismissed: bool

    class Config:
        from_attributes = True

# AI Chat Schemas
class AIChatMessage(BaseModel):
    sender: str  # "user" or "ai"
    text: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class AIChatQuery(BaseModel):
    message: str
    chat_history: List[AIChatMessage] = []

class AIResponse(BaseModel):
    response: str
    action_suggested: Optional[str] = None # e.g., "create_task", "rescue_task", "suggest_schedule"
    parsed_data: Optional[dict] = None
