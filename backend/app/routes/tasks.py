from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import datetime
from app import crud, schemas, models
from app.database import get_db

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/", response_model=List[schemas.Task])
def read_tasks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_tasks(db, skip=skip, limit=limit)


@router.get("/{task_id}", response_model=schemas.Task)
def read_task(task_id: int, db: Session = Depends(get_db)):
    db_task = crud.get_task(db, task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return db_task


@router.post("/", response_model=schemas.Task, status_code=status.HTTP_201_CREATED)
async def create_task(task: schemas.TaskCreate, db: Session = Depends(get_db)):
    db_task = crud.create_task(db=db, task=task)
    from app.agents import EventBus
    await EventBus.publish_event("task_created", {"task_id": db_task.id}, db)
    db.refresh(db_task)
    return db_task


@router.put("/{task_id}", response_model=schemas.Task)
async def update_task(task_id: int, task: schemas.TaskUpdate, db: Session = Depends(get_db)):
    db_task = crud.update_task(db=db, task_id=task_id, task_update=task)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    from app.agents import EventBus
    await EventBus.publish_event("task_updated", {"task_id": db_task.id}, db)
    db.refresh(db_task)
    return db_task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    success = crud.delete_task(db=db, task_id=task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return None


# AI Rescue Trigger — routes any task through the real multi-agent pipeline.
# Uses Gemini (primary) / Groq (fallback) / heuristic fallback.
# Works for ALL tasks, not just seeded demo titles.
@router.post("/{task_id}/rescue", response_model=schemas.Task)
async def rescue_task(task_id: int, db: Session = Depends(get_db)):
    db_task = crud.get_task(db, task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    from app.agents import RescueAgent, NegotiationAgent, PlannerAgent, EventBus

    # Run Planner Agent if no checklist/subtasks exist yet
    if not db_task.subtasks:
        await PlannerAgent.run(db_task, db)

    # Run Rescue Agent — generates contextual rescue strategy via LLM
    await RescueAgent.run(db_task, db, force=True)

    # Run Negotiation Agent — drafts a professional extension email
    await NegotiationAgent.run(db_task, db, force=True)

    # Mark as In Progress
    db_task.status = models.StatusEnum.IN_PROGRESS
    db.commit()

    # Fire the full pipeline so scheduler, predictions, and activity logs all update
    await EventBus.publish_event("task_updated", {"task_id": db_task.id}, db)
    db.refresh(db_task)
    return db_task


@router.post("/{task_id}/subtasks", response_model=schemas.SubTask)
def create_subtask(task_id: int, subtask: schemas.SubTaskCreate, db: Session = Depends(get_db)):
    db_task = crud.get_task(db, task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return crud.create_subtask(db=db, task_id=task_id, subtask=subtask)


@router.put("/subtasks/{subtask_id}", response_model=schemas.SubTask)
async def update_subtask_status(subtask_id: int, is_completed: bool, db: Session = Depends(get_db)):
    db_subtask = crud.update_subtask_status(db=db, subtask_id=subtask_id, is_completed=is_completed)
    if db_subtask is None:
        raise HTTPException(status_code=404, detail="Subtask not found")

    # Event coordination: check if task is completed
    task_id = db_subtask.task_id
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if db_task:
        all_done = all([s.is_completed for s in db_task.subtasks])
        if all_done and db_task.status != models.StatusEnum.COMPLETED:
            db_task.status = models.StatusEnum.COMPLETED
            db_task.completed_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
            db.commit()
            from app.agents import EventBus
            await EventBus.publish_event("task_completed", {"task_id": db_task.id}, db)
        elif not all_done and db_task.status == models.StatusEnum.COMPLETED:
            db_task.status = models.StatusEnum.IN_PROGRESS
            db_task.completed_at = None
            db.commit()
            from app.agents import EventBus
            await EventBus.publish_event("task_updated", {"task_id": db_task.id}, db)
        else:
            from app.agents import EventBus
            await EventBus.publish_event("task_updated", {"task_id": db_task.id}, db)

    return db_subtask


@router.delete("/subtasks/{subtask_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subtask(subtask_id: int, db: Session = Depends(get_db)):
    success = crud.delete_subtask(db=db, subtask_id=subtask_id)
    if not success:
        raise HTTPException(status_code=404, detail="Subtask not found")
    return None


@router.post("/{task_id}/log-focus", response_model=schemas.Task)
async def log_task_focus(task_id: int, minutes: float, db: Session = Depends(get_db)):
    db_task = crud.log_focus_time(db=db, task_id=task_id, minutes=minutes)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    from app.agents import EventBus
    await EventBus.publish_event("task_updated", {"task_id": db_task.id}, db)
    db.refresh(db_task)
    return db_task
