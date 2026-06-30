import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app import crud, schemas, models
from app.database import get_db
from app.agents import EventBus

router = APIRouter(prefix="/schedule", tags=["schedule"])

@router.get("/", response_model=List[schemas.ScheduleBlock])
def read_schedule(db: Session = Depends(get_db)):
    return crud.get_schedule_blocks(db)

@router.post("/", response_model=schemas.ScheduleBlock, status_code=status.HTTP_201_CREATED)
def create_schedule_block(block: schemas.ScheduleBlockCreate, db: Session = Depends(get_db)):
    return crud.create_schedule_block(db=db, block=block)

@router.delete("/{block_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule_block(block_id: int, db: Session = Depends(get_db)):
    success = crud.delete_schedule_block(db=db, block_id=block_id)
    if not success:
        raise HTTPException(status_code=404, detail="Schedule block not found")
    return None

# Google Calendar Event Sync routes
@router.get("/events", response_model=List[schemas.CalendarEvent])
def read_calendar_events(db: Session = Depends(get_db)):
    return db.query(models.CalendarEvent).order_by(models.CalendarEvent.start_time.asc()).all()

@router.post("/events", response_model=schemas.CalendarEvent, status_code=status.HTTP_201_CREATED)
async def create_calendar_event(event: schemas.CalendarEventCreate, db: Session = Depends(get_db)):
    db_event = models.CalendarEvent(
        title=event.title,
        start_time=event.start_time,
        end_time=event.end_time,
        source=event.source,
        is_external=event.is_external
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    
    # Publish calendar event added to event bus to auto-replan schedule
    await EventBus.publish_event("calendar_event_added", {}, db)
    return db_event

@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_calendar_event(event_id: int, db: Session = Depends(get_db)):
    db_event = db.query(models.CalendarEvent).filter(models.CalendarEvent.id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Calendar event not found")
    db.delete(db_event)
    db.commit()
    
    # Replan schedule
    await EventBus.publish_event("calendar_event_added", {}, db)
    return None

@router.post("/auto-plan", response_model=List[schemas.ScheduleBlock])
async def auto_plan_schedule(db: Session = Depends(get_db)):
    """
    Triggers the autonomous agent scheduler to slot tasks around calendar events.
    """
    await EventBus.publish_event("timer_tick", {}, db)
    return crud.get_schedule_blocks(db)

@router.post("/sync-google-calendar", response_model=List[schemas.CalendarEvent])
async def sync_google_calendar(db: Session = Depends(get_db)):
    """
    Hybrid Google Calendar synchronization.
    Mode 1 (Live): If real Google OAuth is connected, fetches events from Google Calendar API.
    Mode 2 (Simulation): Falls back to mock calendar events for demonstration.
    """
    import logging
    logger = logging.getLogger(__name__)

    settings_rec = db.query(models.UserSettings).first()
    refresh_token = settings_rec.google_refresh_token_id if settings_rec else None
    synced_from_google = False

    # --- MODE 1: Real Google Calendar API ---
    if refresh_token:
        try:
            from app.google_services import GoogleCalendarClient
            client = GoogleCalendarClient(refresh_token)

            if client.is_connected():
                # Fetch events for the next 7 days
                now = datetime.datetime.now(datetime.timezone.utc)
                time_min = now.isoformat()
                time_max = (now + datetime.timedelta(days=7)).isoformat()

                google_events = client.get_events(time_min, time_max)

                # Filter out our own LMLS focus blocks
                google_events = [ev for ev in google_events if 'LMLS' not in ev.get('description', '')]

                if google_events:
                    # Clear old external events and replace with fresh Google data
                    db.query(models.CalendarEvent).filter(
                        models.CalendarEvent.source == "Google Calendar"
                    ).delete()
                    db.commit()

                    for ev in google_events:
                        db_event = models.CalendarEvent(
                            title=ev["title"],
                            start_time=datetime.datetime.fromisoformat(ev["start_time"].replace("Z", "+00:00")).replace(tzinfo=None),
                            end_time=datetime.datetime.fromisoformat(ev["end_time"].replace("Z", "+00:00")).replace(tzinfo=None),
                            source="Google Calendar",
                            is_external=True
                        )
                        db.add(db_event)
                    db.commit()
                    synced_from_google = True
                    logger.info(f"Synced {len(google_events)} events from Google Calendar API.")

                    from app.agents import AgentLogger
                    await AgentLogger.log_activity(
                        "Google Calendar Sync",
                        f"Live sync: Imported {len(google_events)} events from Google Calendar API.",
                        db
                    )
        except Exception as e:
            logger.error(f"Google Calendar live sync failed, falling back to simulation: {e}")

    # --- MODE 2: Simulation Fallback ---
    if not synced_from_google:
        existing_events = db.query(models.CalendarEvent).all()
        if not existing_events:
            tomorrow = datetime.date.today() + datetime.timedelta(days=1)
            mock_events = [
                models.CalendarEvent(
                    title="Weekly Synch meeting with manager",
                    start_time=datetime.datetime.combine(tomorrow, datetime.time(10, 0)),
                    end_time=datetime.datetime.combine(tomorrow, datetime.time(11, 0)),
                    source="Google Calendar",
                    is_external=True
                ),
                models.CalendarEvent(
                    title="Product Architecture Brainstorming",
                    start_time=datetime.datetime.combine(tomorrow, datetime.time(14, 0)),
                    end_time=datetime.datetime.combine(tomorrow, datetime.time(15, 30)),
                    source="Google Calendar",
                    is_external=True
                )
            ]
            db.add_all(mock_events)
            db.commit()
        
    # Mark account connected
    if settings_rec:
        settings_rec.google_account_connected = True
        db.commit()

    # Replan schedule using event bus
    await EventBus.publish_event("calendar_event_added", {}, db)
    return db.query(models.CalendarEvent).all()

@router.put("/events/{event_id}", response_model=schemas.CalendarEvent)
async def update_calendar_event(event_id: int, event: schemas.CalendarEventCreate, db: Session = Depends(get_db)):
    db_event = db.query(models.CalendarEvent).filter(models.CalendarEvent.id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Calendar event not found")
    db_event.title = event.title
    db_event.start_time = event.start_time
    db_event.end_time = event.end_time
    db_event.source = event.source
    db_event.is_external = event.is_external
    db.commit()
    db.refresh(db_event)
    
    # Replan schedule
    await EventBus.publish_event("calendar_event_added", {}, db)
    return db_event
