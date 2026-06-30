import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app import models, schemas

# Helper to calculate panic index dynamically
def compute_panic_index(task: models.Task) -> float:
    if task.status == models.StatusEnum.COMPLETED:
        return 0.0
    
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    due_date = task.due_date
    if due_date and due_date.tzinfo is not None:
        due_date = due_date.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    time_left = due_date - now
    hours_left = time_left.total_seconds() / 3600.0
    
    # Priority multipliers
    priority_weights = {
        models.PriorityEnum.LOW: 0.5,
        models.PriorityEnum.MEDIUM: 1.0,
        models.PriorityEnum.HIGH: 1.5,
        models.PriorityEnum.URGENT: 2.0
    }
    weight = priority_weights.get(task.priority, 1.0)
    
    if hours_left <= 0:
        # Overdue
        return 10.0 + abs(hours_left) * 0.1
    
    # Calculate panic score
    score = (task.estimated_hours / hours_left) * weight
    return round(score, 3)

def update_task_panic_indices(db: Session):
    tasks = db.query(models.Task).filter(models.Task.status != models.StatusEnum.COMPLETED).all()
    for task in tasks:
        task.panic_index = compute_panic_index(task)
        # Check if overdue
        due_date = task.due_date
        if due_date and due_date.tzinfo is not None:
            due_date = due_date.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        if due_date < datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) and task.status != models.StatusEnum.COMPLETED:
            task.status = models.StatusEnum.OVERDUE
    db.commit()

# Task CRUD operations
def get_tasks(db: Session, skip: int = 0, limit: int = 100):
    update_task_panic_indices(db)
    return db.query(models.Task).order_by(desc(models.Task.panic_index)).offset(skip).limit(limit).all()

def get_task(db: Session, task_id: int):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if task:
        task.panic_index = compute_panic_index(task)
        due_date = task.due_date
        if due_date and due_date.tzinfo is not None:
            due_date = due_date.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        if due_date < datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) and task.status != models.StatusEnum.COMPLETED:
            task.status = models.StatusEnum.OVERDUE
            db.commit()
    return task

def create_task(db: Session, task: schemas.TaskCreate):
    due_date = task.due_date
    if due_date and due_date.tzinfo is not None:
        due_date = due_date.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    db_task = models.Task(
        title=task.title,
        description=task.description,
        due_date=due_date,
        priority=task.priority if task.priority is not None else models.PriorityEnum.MEDIUM,
        status=models.StatusEnum.PENDING,
        estimated_hours=task.estimated_hours if task.estimated_hours is not None else 1.0,
        category=task.category if task.category is not None else "Work"
    )
    db_task.panic_index = compute_panic_index(db_task)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # Add subtasks if provided
    for sub in task.subtasks:
        db_sub = models.SubTask(
            task_id=db_task.id,
            title=sub.title,
            is_completed=sub.is_completed,
            estimated_minutes=sub.estimated_minutes,
            order=sub.order
        )
        db.add(db_sub)
    
    db.commit()
    db.refresh(db_task)
    return db_task

def update_task(db: Session, task_id: int, task_update: schemas.TaskUpdate):
    db_task = get_task(db, task_id)
    if not db_task:
        return None
    
    update_data = task_update.model_dump(exclude_unset=True)
    if "due_date" in update_data and update_data["due_date"] is not None:
        due_date = update_data["due_date"]
        if due_date.tzinfo is not None:
            update_data["due_date"] = due_date.astimezone(datetime.timezone.utc).replace(tzinfo=None)
            
    for key, value in update_data.items():
        setattr(db_task, key, value)
    
    if db_task.status == models.StatusEnum.COMPLETED:
        db_task.completed_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        db_task.panic_index = 0.0
    else:
        db_task.completed_at = None
        db_task.panic_index = compute_panic_index(db_task)
        
    db.commit()
    db.refresh(db_task)
    return db_task

def delete_task(db: Session, task_id: int):
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if db_task:
        db.delete(db_task)
        db.commit()
        return True
    return False

# SubTask CRUD operations
def create_subtask(db: Session, task_id: int, subtask: schemas.SubTaskCreate):
    db_subtask = models.SubTask(**subtask.model_dump(), task_id=task_id)
    db.add(db_subtask)
    db.commit()
    db.refresh(db_subtask)
    return db_subtask

def update_subtask_status(db: Session, subtask_id: int, is_completed: bool):
    db_subtask = db.query(models.SubTask).filter(models.SubTask.id == subtask_id).first()
    if not db_subtask:
        return None
    db_subtask.is_completed = is_completed
    db.commit()
    db.refresh(db_subtask)
    return db_subtask

def delete_subtask(db: Session, subtask_id: int):
    db_subtask = db.query(models.SubTask).filter(models.SubTask.id == subtask_id).first()
    if db_subtask:
        db.delete(db_subtask)
        db.commit()
        return True
    return False

# Schedule Block CRUD
def get_schedule_blocks(db: Session):
    return db.query(models.ScheduleBlock).all()

def create_schedule_block(db: Session, block: schemas.ScheduleBlockCreate):
    db_block = models.ScheduleBlock(**block.model_dump())
    db.add(db_block)
    db.commit()
    db.refresh(db_block)
    return db_block

def delete_schedule_block(db: Session, block_id: int):
    db_block = db.query(models.ScheduleBlock).filter(models.ScheduleBlock.id == block_id).first()
    if db_block:
        db.delete(db_block)
        db.commit()
        return True
    return False

# Habit CRUD operations
def get_habits(db: Session):
    return db.query(models.Habit).all()

def create_habit(db: Session, habit: schemas.HabitCreate):
    db_habit = models.Habit(title=habit.title, frequency=habit.frequency)
    db.add(db_habit)
    db.commit()
    db.refresh(db_habit)
    return db_habit

def log_habit(db: Session, habit_id: int, log_date: datetime.date):
    # Check if log already exists
    existing = db.query(models.HabitLog).filter(
        models.HabitLog.habit_id == habit_id,
        models.HabitLog.completed_date == log_date
    ).first()
    if existing:
        return existing
    
    db_habit = db.query(models.Habit).filter(models.Habit.id == habit_id).first()
    if not db_habit:
        return None
    
    # Log details
    db_log = models.HabitLog(habit_id=habit_id, completed_date=log_date)
    db.add(db_log)
    
    # Calculate streak
    if db_habit.last_completed_date:
        delta = log_date - db_habit.last_completed_date
        if delta.days == 1:
            db_habit.streak += 1
        elif delta.days > 1:
            db_habit.streak = 1
    else:
        db_habit.streak = 1
        
    db_habit.last_completed_date = log_date
    db.commit()
    db.refresh(db_habit)
    return db_log

def delete_habit(db: Session, habit_id: int):
    db_habit = db.query(models.Habit).filter(models.Habit.id == habit_id).first()
    if db_habit:
        db.delete(db_habit)
        db.commit()
        return True
    return False

# Recommendation CRUD operations
def get_recommendations(db: Session):
    return db.query(models.Recommendation).filter(models.Recommendation.dismissed == False).all()

def create_recommendation(db: Session, content: str, category: str):
    # Avoid duplicate recommendations
    existing = db.query(models.Recommendation).filter(
        models.Recommendation.content == content,
        models.Recommendation.dismissed == False
    ).first()
    if existing:
        return existing
    
    db_rec = models.Recommendation(content=content, category=category)
    db.add(db_rec)
    db.commit()
    db.refresh(db_rec)
    return db_rec

def dismiss_recommendation(db: Session, rec_id: int):
    db_rec = db.query(models.Recommendation).filter(models.Recommendation.id == rec_id).first()
    if db_rec:
        db_rec.dismissed = True
        db.commit()
        return True
    return False

def log_focus_time(db: Session, task_id: int, minutes: float) -> models.Task:
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if db_task:
        db_task.actual_hours_spent += minutes / 60.0
        db.commit()
        db.refresh(db_task)
    return db_task
