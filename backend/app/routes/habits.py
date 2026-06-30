import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/habits", tags=["habits"])

@router.get("/", response_model=List[schemas.Habit])
def read_habits(db: Session = Depends(get_db)):
    return crud.get_habits(db)

@router.post("/", response_model=schemas.Habit, status_code=status.HTTP_201_CREATED)
def create_habit(habit: schemas.HabitCreate, db: Session = Depends(get_db)):
    return crud.create_habit(db=db, habit=habit)

@router.post("/{habit_id}/log", response_model=schemas.HabitLog)
def log_habit(habit_id: int, log_data: schemas.HabitLogCreate, db: Session = Depends(get_db)):
    db_log = crud.log_habit(db=db, habit_id=habit_id, log_date=log_data.completed_date)
    if db_log is None:
        raise HTTPException(status_code=404, detail="Habit not found")
    return db_log

@router.delete("/{habit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_habit(habit_id: int, db: Session = Depends(get_db)):
    success = crud.delete_habit(db=db, habit_id=habit_id)
    if not success:
        raise HTTPException(status_code=404, detail="Habit not found")
    return None
