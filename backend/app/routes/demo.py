from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
import datetime
from app import models
from app.database import get_db

router = APIRouter(prefix="/demo", tags=["demo"])


async def autonomous_pipeline_after_seed(db: Session):
    """Fires the full multi-agent pipeline after demo seeding to populate the activity feed."""
    try:
        from app.agents import EventBus
        await EventBus.publish_event("timer_tick", {}, db)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Post-seed pipeline error: {e}")


class DemoSeedRequest(BaseModel):
    scenario: str


@router.post("/seed", status_code=status.HTTP_200_OK)
async def seed_demo_scenario(payload: DemoSeedRequest, db: Session = Depends(get_db)):
    """
    Clears current workspace database tables and seeds scenario-specific realistic datasets.
    """
    scenario = payload.scenario.lower()
    if scenario not in ["student", "professional", "startup"]:
        raise HTTPException(status_code=400, detail="Invalid scenario name")

    try:
        # Clear tables
        db.query(models.SubTask).delete()
        db.query(models.ScheduleBlock).delete()
        db.query(models.EmailDraft).delete()
        db.query(models.Task).delete()
        db.query(models.CalendarEvent).delete()
        db.query(models.Notification).delete()
        db.query(models.AgentActivity).delete()
        db.query(models.HabitLog).delete()
        db.query(models.Habit).delete()
        db.query(models.Recommendation).delete()
        db.commit()

        # Seed defaults if not present
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

        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

        tasks_count = 0
        events_count = 0
        drafts_count = 0
        logs_count = 0
        notifs_count = 0

        if scenario == "student":
            # 🎓 STUDENT MODE SEEDING
            # Task 1 (Urgent, low success, needs rescue)
            task_urgent = models.Task(
                title="Submit Operating Systems Assignment",
                description="Implement kernel scheduling simulator and compile drivers.",
                due_date=now + datetime.timedelta(hours=2),
                priority=models.PriorityEnum.URGENT,
                status=models.StatusEnum.IN_PROGRESS,
                estimated_hours=3.5,
                category="Academic",
                panic_index=3.8,
                completion_probability=0.18,
                impact="High",
                reward="Secure grade criteria and preserve semester GPA.",
                loss_if_skipped="Forfeit 15% grade contribution and risk course repeat.",
                ai_reasoning="Critical core deadline in 2 hours with 3.5 hours of work estimated. Completion is mathematically impossible without immediate scope reduction."
            )
            db.add(task_urgent)
            tasks_count += 1

            # Task 2 (Normal pending)
            task_pending1 = models.Task(
                title="Prepare for Calculus Quiz",
                description="Review integration by parts and trigonometric substitution.",
                due_date=now + datetime.timedelta(hours=24),
                priority=models.PriorityEnum.HIGH,
                status=models.StatusEnum.PENDING,
                estimated_hours=4.0,
                category="Academic",
                panic_index=1.2,
                completion_probability=0.78,
                impact="Medium",
                ai_reasoning="Calculus Quiz scheduled tomorrow. Sufficient buffer time exists to complete focus review block."
            )
            db.add(task_pending1)
            tasks_count += 1

            # Task 3 (Normal pending)
            task_pending2 = models.Task(
                title="Submit Chemistry Project Slides",
                description="Compile lab results on atomic structures and render outlines.",
                due_date=now + datetime.timedelta(hours=36),
                priority=models.PriorityEnum.MEDIUM,
                status=models.StatusEnum.PENDING,
                estimated_hours=2.0,
                category="Academic",
                panic_index=0.8,
                completion_probability=0.88,
                impact="Low",
                ai_reasoning="Lower urgency milestone. Recommend focusing on immediate OS Assignment first."
            )
            db.add(task_pending2)
            tasks_count += 1

            # Task 4 (Completed)
            task_completed = models.Task(
                title="Database Lab Practical",
                description="Write SQL statements for nested joins.",
                due_date=now - datetime.timedelta(hours=12),
                priority=models.PriorityEnum.MEDIUM,
                status=models.StatusEnum.COMPLETED,
                estimated_hours=1.5,
                category="Academic",
                panic_index=0.0,
                completion_probability=1.0,
                completed_at=now - datetime.timedelta(hours=14)
            )
            db.add(task_completed)
            tasks_count += 1

            # Habits
            habit1 = models.Habit(title="Morning LeetCode Check-in", frequency=models.HabitFrequencyEnum.DAILY, streak=7, last_completed_date=(now - datetime.timedelta(days=1)).date())
            db.add(habit1)
            
            # Agent Activities
            activities = [
                ("Planner Agent", "Registered OS Assignment deadlines into the schedule matrices."),
                ("Risk Detector", "Flagged 'Submit Operating Systems Assignment' with critical 18% completion risk."),
                ("Prioritization Agent", "Elevated OS Assignment panic index due to close deadline window.")
            ]
            for agent, action in activities:
                db.add(models.AgentActivity(agent_name=agent, action_taken=action, timestamp=now - datetime.timedelta(minutes=5)))
                logs_count += 1

            # Notifications
            db.add(models.Notification(message="🚨 Alert: 'Submit Operating Systems Assignment' completion probability dropped to 18%!", type="urgent"))
            notifs_count += 1

            # Recommendation
            db.add(models.Recommendation(content="Consider triggering AI Rescue Mode immediately for your OS Assignment to prune scheduling tasks.", category="Urgency"))

        elif scenario == "professional":
            # 💼 PROFESSIONAL MODE SEEDING
            # Task 1 (Urgent incident task)
            task_urgent = models.Task(
                title="Deploy Bug Fix for Production Checkout Crash",
                description="Fix NullPointerException on billing info checkout submission.",
                due_date=now + datetime.timedelta(hours=3),
                priority=models.PriorityEnum.URGENT,
                status=models.StatusEnum.IN_PROGRESS,
                estimated_hours=2.5,
                category="Work",
                panic_index=4.2,
                completion_probability=0.22,
                impact="High",
                reward="Restore customer billing service operations and recover conversion logs.",
                loss_if_skipped="Ongoing business revenue loss and elevated checkout bounce rates.",
                ai_reasoning="Critical production crash checkout blocking users. Unscheduled client alignment sync conflict limits available focus slots."
            )
            db.add(task_urgent)
            tasks_count += 1

            # Task 2 (Normal work pending)
            task_pending = models.Task(
                title="Review Auth Service Pull Request",
                description="Verify token expiry checks and OAuth refresh callbacks.",
                due_date=now + datetime.timedelta(hours=18),
                priority=models.PriorityEnum.HIGH,
                status=models.StatusEnum.PENDING,
                estimated_hours=1.5,
                category="Work",
                panic_index=1.5,
                completion_probability=0.74,
                impact="Medium",
                ai_reasoning="Important auth security review. Schedulable after resolving the checkout incident hotfix."
            )
            db.add(task_pending)
            tasks_count += 1

            # Task 3 (Completed Work)
            task_completed = models.Task(
                title="Sprint Planning Alignment Sync",
                description="Commit backlog issues and map milestones for the Q3 release.",
                due_date=now - datetime.timedelta(hours=8),
                priority=models.PriorityEnum.MEDIUM,
                status=models.StatusEnum.COMPLETED,
                estimated_hours=1.0,
                category="Work",
                panic_index=0.0,
                completion_probability=1.0,
                completed_at=now - datetime.timedelta(hours=9)
            )
            db.add(task_completed)
            tasks_count += 1

            # Calendar Conflict (Rescheduling Wow Moment!)
            conflict_event = models.CalendarEvent(
                title="Urgent Client Alignment Sync",
                start_time=now + datetime.timedelta(minutes=30),
                end_time=now + datetime.timedelta(minutes=90),
                source="Google Calendar",
                is_external=True
            )
            db.add(conflict_event)
            events_count += 1

            # Flush to get IDs before adding dependent records
            db.flush()

            # Schedule Blocks (rescheduled around calendar event)
            block1 = models.ScheduleBlock(
                task_id=task_urgent.id,  # Use actual assigned ID, not hardcoded 1
                start_time=now + datetime.timedelta(minutes=95),
                end_time=now + datetime.timedelta(minutes=155),
                is_focus_block=True
            )
            db.add(block1)

            # Habits
            habit1 = models.Habit(title="Daily Standup Check-in", frequency=models.HabitFrequencyEnum.DAILY, streak=12, last_completed_date=(now - datetime.timedelta(days=1)).date())
            db.add(habit1)

            # Agent Activities
            activities = [
                ("Scheduler Agent", "Conflict detected with external meeting 'Urgent Client Alignment Sync'. Focus block for Bug Fix rescheduled to next business slot."),
                ("Risk Detector", "Flagged production checkout crash completion probability at 22% due to meeting overlap."),
                ("Prioritization Agent", "Ranked Checkout crash fix as highest Priority core target.")
            ]
            for agent, action in activities:
                db.add(models.AgentActivity(agent_name=agent, action_taken=action, timestamp=now - datetime.timedelta(minutes=5)))
                logs_count += 1

            # Notifications
            db.add(models.Notification(message="🚨 Reschedule Alert: Checkout crash block shifted to accommodate Client Sync.", type="warning"))
            notifs_count += 1

            # Recommendation
            db.add(models.Recommendation(content="Deploying Checkout crash requires uninterrupted focus. Apologize to manager via the pre-written negotiation draft.", category="Analytics"))

        elif scenario == "startup":
            # 🚀 STARTUP FOUNDER MODE SEEDING
            # Task 1 (Investor Pitch)
            task_urgent = models.Task(
                title="Finish Investor Pitch Deck for Series A Pitch",
                description="Consolidate traction charts, unit economics, and pipeline financials.",
                due_date=now + datetime.timedelta(hours=4),
                priority=models.PriorityEnum.URGENT,
                status=models.StatusEnum.IN_PROGRESS,
                estimated_hours=4.5,
                category="Work",
                panic_index=4.9,
                completion_probability=0.12,
                impact="High",
                reward="Secure critical funding round commitments and launch operational scale.",
                loss_if_skipped="Forfeit Series A term sheet closing window and risk runway exhaustion.",
                ai_reasoning="Critical investment milestone in 4 hours. 4.5 hours of deck assembly left. Threat radar highlights extreme panic; immediate rescue pruning advised."
            )
            db.add(task_urgent)
            tasks_count += 1

            # Task 2 (Normal Startup pending)
            task_pending = models.Task(
                title="Prepare Demo Day Showcase",
                description="Rehearse product demo script and test live API loads.",
                due_date=now + datetime.timedelta(hours=28),
                priority=models.PriorityEnum.HIGH,
                status=models.StatusEnum.PENDING,
                estimated_hours=3.0,
                category="Work",
                panic_index=1.6,
                completion_probability=0.72,
                impact="Medium",
                ai_reasoning="Pre-demo staging checkpoint tomorrow. Recommend completing pitch deck rescue before entering demo rehearsal blocks."
            )
            db.add(task_pending)
            tasks_count += 1

            # Habits
            habit1 = models.Habit(title="Sync with Co-founders", frequency=models.HabitFrequencyEnum.DAILY, streak=8, last_completed_date=(now - datetime.timedelta(days=1)).date())
            db.add(habit1)

            # Agent Activities
            activities = [
                ("Risk Detector", "Investor Pitch Deck completion probability dropped to 12%. Emergency Rescue Mode triggered."),
                ("Planner Agent", "Decomposed 'Investor Pitch Deck' into core traction slides."),
                ("Prioritization Agent", "Sorted workspace task backlog; flagged VC Pitch Deck as critical founder output.")
            ]
            for agent, action in activities:
                db.add(models.AgentActivity(agent_name=agent, action_taken=action, timestamp=now - datetime.timedelta(minutes=5)))
                logs_count += 1

            # Notifications
            db.add(models.Notification(message="🚨 Urgent: Pitch deck probability is 12%. AI Rescue strategy is ready to boost performance.", type="urgent"))
            notifs_count += 1

            # Recommendation
            db.add(models.Recommendation(content="Trim non-essential team details and draft investment extension pitch updates now.", category="Analytics"))

        db.commit()

        # Fire the autonomous agent pipeline so the activity feed populates immediately
        # This makes the Event Bus appear active right after scenario load
        from app.agents import EventBus
        await autonomous_pipeline_after_seed(db)

        # Gather details for return response
        seeded_info = {
            "tasks": tasks_count,
            "calendar_events": events_count,
            "email_drafts": drafts_count,
            "agent_logs": logs_count,
            "notifications": notifs_count
        }

        return {
            "status": "success",
            "scenario": scenario,
            "seeded_records": seeded_info
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database seeding failed: {str(e)}")
