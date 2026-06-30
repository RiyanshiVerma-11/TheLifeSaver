import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base, SessionLocal
from app.routes import tasks, habits, schedule, ai, negotiation, demo, oauth
from app.config import settings
from sqlalchemy import inspect, text
from app import models

logger = logging.getLogger(__name__)

# Try importing apscheduler to support environments where it might not be installed
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore # pyright: ignore[reportMissingImports]
    HAS_APSCHEDULER = True
except ImportError:
    HAS_APSCHEDULER = False
    logger.warning("⚠️ apscheduler module not found. Background timer will be disabled.")

# Initialize database models
inspector = inspect(engine)
tables = inspector.get_table_names()

if "tasks" in tables:
    task_columns = [col["name"] for col in inspector.get_columns("tasks")]
    with engine.begin() as conn:
        if "actual_hours_spent" not in task_columns:
            print("⚠️ Adding actual_hours_spent to tasks table...")
            conn.execute(text("ALTER TABLE tasks ADD COLUMN actual_hours_spent FLOAT DEFAULT 0.0"))
        if "impact" not in task_columns:
            print("⚠️ Adding impact to tasks table...")
            conn.execute(text("ALTER TABLE tasks ADD COLUMN impact VARCHAR DEFAULT 'Medium'"))
        if "gcal_event_id" not in task_columns:
            print("⚠️ Adding gcal_event_id to tasks table...")
            conn.execute(text("ALTER TABLE tasks ADD COLUMN gcal_event_id VARCHAR"))

if "user_settings" in tables:
    settings_columns = [col["name"] for col in inspector.get_columns("user_settings")]
    with engine.begin() as conn:
        if "start_work_hour" not in settings_columns:
            print("⚠️ Adding start_work_hour to user_settings table...")
            conn.execute(text("ALTER TABLE user_settings ADD COLUMN start_work_hour INTEGER DEFAULT 9"))
        if "google_oauth_code_verifier" not in settings_columns:
            print("⚠️ Adding google_oauth_code_verifier to user_settings table...")
            conn.execute(text("ALTER TABLE user_settings ADD COLUMN google_oauth_code_verifier VARCHAR"))

if "schedule_blocks" in tables:
    blocks_columns = [col["name"] for col in inspector.get_columns("schedule_blocks")]
    with engine.begin() as conn:
        if "gcal_event_id" not in blocks_columns:
            print("⚠️ Adding gcal_event_id to schedule_blocks table...")
            conn.execute(text("ALTER TABLE schedule_blocks ADD COLUMN gcal_event_id VARCHAR"))

Base.metadata.create_all(bind=engine)

# Seed default settings and configs
db = SessionLocal()
try:
    if not db.query(models.UserSettings).first():
        db.add(models.UserSettings(
            sleep_hours=8.0,
            meeting_load_hours=2.0,
            daily_focus_target=4.0,
            google_account_connected=False,
            start_work_hour=9,
            end_work_hour=18
        ))
    if not db.query(models.RiskEngineConfig).first():
        db.add(models.RiskEngineConfig(
            threshold_warning=0.70,
            threshold_critical=0.40,
            prediction_window_hours=48
        ))
    db.commit()
except Exception as e:
    print(f"Error seeding database: {e}")
finally:
    db.close()


# Background autonomous timer tick — runs every 5 minutes
async def autonomous_timer_tick():
    """
    Fires the multi-agent pipeline autonomously every 5 minutes,
    updating panic indices, completion probabilities, and triggering
    rescue/negotiation agents for any at-risk tasks.
    """
    from app.agents import EventBus
    db = SessionLocal()
    try:
        logger.info("⏰ Background autonomous timer tick fired.")
        await EventBus.publish_event("timer_tick", {}, db)
    except Exception as e:
        db.rollback()
        logger.error(f"Background timer error: {e}")
    finally:
        db.close()


scheduler = None
if HAS_APSCHEDULER:
    scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: launch background scheduler if available
    if HAS_APSCHEDULER and scheduler:
        scheduler.add_job(
            autonomous_timer_tick,
            trigger="interval",
            minutes=5,
            id="autonomous_tick",
            replace_existing=True
        )
        scheduler.start()
        logger.info("✅ Autonomous background scheduler started (5-minute interval).")
    else:
        logger.warning("⚠️ Background autonomous timer is disabled (apscheduler unavailable).")
    yield
    # Shutdown: stop scheduler cleanly if it was running
    if HAS_APSCHEDULER and scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped.")


app = FastAPI(
    title="The Last-Minute Life Saver API",
    description="AI-powered productivity agent core backend service",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, configure this specifically
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(tasks.router, prefix="/api")
app.include_router(habits.router, prefix="/api")
app.include_router(schedule.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(negotiation.router, prefix="/api")
app.include_router(demo.router, prefix="/api")
app.include_router(oauth.router, prefix="/api")


@app.get("/api/health")
def health_check():
    from app.google_services import is_google_oauth_configured
    return {
        "status": "healthy",
        "autonomous_scheduler": "running" if (HAS_APSCHEDULER and scheduler and scheduler.running) else "disabled/unsupported",
        "api_keys_loaded": {
            "gemini": bool(settings.GEMINI_API_KEY),
            "groq": bool(settings.GROQ_API_KEY)
        },
        "google_oauth_ready": is_google_oauth_configured(),
        "llm_structured_outputs": True,
        "agents_with_llm": 9
    }
