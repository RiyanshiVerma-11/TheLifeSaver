import json
import logging
import datetime
from datetime import timedelta, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app import models, schemas
from app.ai_agent import call_llm, clean_json_text

logger = logging.getLogger(__name__)

# --- AUTONOMOUS EVENT BUS ---
class EventBus:
    @staticmethod
    async def publish_event(event_type: str, payload: dict, db: Session):
        """
        Publishes system events to trigger multi-agent pipeline executions.
        Events: 'task_created', 'task_updated', 'task_completed', 
                'calendar_event_added', 'focus_session_missed', 'timer_tick'
        """
        action_log = f"Event Bus received: '{event_type}'."
        logger.info(action_log)
        await AgentLogger.log_activity("Event Bus", f"Intercepted system event: {event_type}", db)

        # Base orchestrator acts upon the event
        await MultiAgentOrchestrator.run_pipeline(event_type, payload, db)


# --- AGENT LOGGING ASSISTANT ---
class AgentLogger:
    @staticmethod
    async def log_activity(agent_name: str, action: str, db: Session):
        activity = models.AgentActivity(
            agent_name=agent_name,
            action_taken=action,
            timestamp=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        )
        db.add(activity)
        db.commit()


# --- MULTI-AGENT ORCHESTRATOR ---
class MultiAgentOrchestrator:
    @staticmethod
    async def run_pipeline(event_type: str, payload: dict, db: Session):
        """
        Executes the agent pipeline sequentially:
        Planner -> Prioritizer -> Scheduler -> Prediction Engine -> Risk Detector ->
        [If Risk: Rescue -> Negotiation] -> Motivation -> Reflection (if completed) -> Update DB
        """
        try:
            task_id = payload.get("task_id")
            task = None
            if task_id:
                task = db.query(models.Task).filter(models.Task.id == task_id).first()

            # 1. Planner Agent
            if event_type == "task_created" and task:
                await PlannerAgent.run(task, db)

            # 2. Prioritization Agent
            # Updates Panic Index and Opportunity Cost Trade-offs
            await PrioritizationAgent.run(db)

            # 3. Scheduler Agent
            # Blocks focus Pomodoros, handles Google Calendar conflict avoidance
            await SchedulerAgent.run(db)

            # 4. AI Prediction & Risk Forecasting Engine
            # Calculates probability of completion
            if task:
                await AIPredictionEngine.run(task, db)
            else:
                # Update for all active tasks
                active_tasks = db.query(models.Task).filter(models.Task.status != models.StatusEnum.COMPLETED).all()
                for t in active_tasks:
                    await AIPredictionEngine.run(t, db)

            # 5. Risk Detector Agent
            # Classifies risk state and triggers rescues / negotiations
            if task:
                await RiskDetector.run(task, db)
            else:
                active_tasks = db.query(models.Task).filter(models.Task.status != models.StatusEnum.COMPLETED).all()
                for t in active_tasks:
                    await RiskDetector.run(t, db)

            # 6. Reflection Agent
            # Executes when a task is completed to update AI Memory
            if event_type == "task_completed" and task:
                await ReflectionAgent.run(task, db)

            # Refresh task state
            if task:
                db.refresh(task)
            
            await AgentLogger.log_activity("Orchestrator", "Multi-Agent pipeline executed successfully.", db)
        except Exception as e:
            logger.error(f"Pipeline Execution Error: {str(e)}")
            await AgentLogger.log_activity("Orchestrator", f"Pipeline encountered error: {str(e)[:100]}", db)


# --- 1. PLANNER AGENT ---
class PlannerAgent:
    @staticmethod
    async def run(task: models.Task, db: Session):
        await AgentLogger.log_activity("Planner Agent", f"Planning task outline for '{task.title}'", db)
        # Check if subtasks already exist. If not, auto-generate.
        if not task.subtasks:
            system_prompt = (
                "You are an expert AI task planner. Break down the user's task into 3 to 5 actionable subtasks. "
                "Output ONLY a JSON list of objects containing 'title' and 'estimated_minutes' (integer)."
            )
            user_prompt = f"Task: {task.title}\nDescription: {task.description or ''}"
            
            try:
                res = await call_llm(system_prompt, user_prompt, json_mode=True)
                cleaned = clean_json_text(res)
                subtasks = json.loads(cleaned)
                
                for i, sub in enumerate(subtasks):
                    db_sub = models.SubTask(
                        task_id=task.id,
                        title=sub.get("title", f"Subtask {i+1}"),
                        is_completed=False,
                        estimated_minutes=int(sub.get("estimated_minutes", 30)),
                        order=i
                    )
                    db.add(db_sub)
                db.commit()
                await AgentLogger.log_activity("Planner Agent", f"Generated {len(subtasks)} checklists for '{task.title}'", db)
            except Exception as e:
                logger.error(f"Planner Agent error: {e}")
                # Fallback heuristics
                defaults = [
                    ("Initial preparation & research", 20),
                    ("Execute core requirements", 45),
                    ("Review, edit and finalize", 15)
                ]
                for i, (title, duration) in enumerate(defaults):
                    db_sub = models.SubTask(
                        task_id=task.id,
                        title=title,
                        is_completed=False,
                        estimated_minutes=duration,
                        order=i
                    )
                    db.add(db_sub)
                db.commit()
                await AgentLogger.log_activity("Planner Agent", f"Applied fallback checklist breakdown for '{task.title}'", db)


# --- 2. PRIORITIZATION AGENT ---
class PrioritizationAgent:
    @staticmethod
    async def run(db: Session):
        await AgentLogger.log_activity("Prioritization Agent", "Evaluating task priorities and computing Panic Indices.", db)
        
        tasks = db.query(models.Task).filter(models.Task.status != models.StatusEnum.COMPLETED).all()
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

        # Update panic indices first
        for task in tasks:
            due_date = task.due_date
            if due_date.tzinfo is not None:
                due_date = due_date.astimezone(datetime.timezone.utc).replace(tzinfo=None)
            
            time_left = due_date - now
            hours_left = time_left.total_seconds() / 3600.0

            priority_multipliers = {
                models.PriorityEnum.LOW: 0.5,
                models.PriorityEnum.MEDIUM: 1.0,
                models.PriorityEnum.HIGH: 1.5,
                models.PriorityEnum.URGENT: 2.0
            }
            mult = priority_multipliers.get(task.priority, 1.0)

            if hours_left <= 0:
                task.panic_index = min(10.0 + abs(hours_left) * 0.1, 20.0)
                task.status = models.StatusEnum.OVERDUE
            else:
                # Clamp to max 20.0 to prevent division by near-zero producing garbage values
                task.panic_index = round(min((task.estimated_hours / max(hours_left, 0.1)) * mult, 20.0), 3)
            
        db.commit()

        # Perform Opportunity Cost reasoning for active tasks
        active_tasks = sorted(tasks, key=lambda t: t.panic_index, reverse=True)
        if len(active_tasks) > 1:
            for idx, task in enumerate(active_tasks):
                next_tasks = active_tasks[idx+1:]
                if next_tasks:
                    competing = next_tasks[0]
                    task.impact = "High" if task.priority in [models.PriorityEnum.URGENT, models.PriorityEnum.HIGH] else "Medium"
                    task.reward = f"Complete critical deliverable '{task.title}' and maintain progress streak."
                    task.loss_if_skipped = f"Delaying this will force '{competing.title}' to slide, increasing stress probability."
                    task.ai_reasoning = (
                        f"Prioritized '{task.title}' (Panic Score: {task.panic_index}) over '{competing.title}' "
                        f"(Panic Score: {competing.panic_index}) based on remaining time vs estimated effort. "
                        f"Postponing this will reduce success probability of subsequent tasks."
                    )
                else:
                    task.impact = "Medium"
                    task.reward = f"Complete standard deliverable '{task.title}'."
                    task.loss_if_skipped = "Slight delay in timeline padding."
                    task.ai_reasoning = f"This task stands alone in the timeline backlog; scheduling for immediate focus."
        elif active_tasks:
            task = active_tasks[0]
            task.impact = "High" if task.priority == models.PriorityEnum.URGENT else "Medium"
            task.reward = "Fulfill upcoming task milestone."
            task.loss_if_skipped = "Forfeit streak progress."
            task.ai_reasoning = "Only active task in focus window. Initializing immediate execution block."

        db.commit()


# --- 3. SCHEDULER AGENT ---
class SchedulerAgent:
    @staticmethod
    async def run(db: Session):
        await AgentLogger.log_activity("Scheduler Agent", "Reviewing schedules and resolving calendar conflicts.", db)
        
        # Get external calendar events
        gcal_events = db.query(models.CalendarEvent).all()
        # Get active tasks
        tasks = db.query(models.Task).filter(models.Task.status != models.StatusEnum.COMPLETED).order_by(models.Task.panic_index.desc()).all()
        
        if not tasks:
            return

        # Clear old focus blocks
        db.query(models.ScheduleBlock).delete()
        db.commit()

        # Retrieve user configured work hours from settings (default to 9 AM to 6 PM)
        user_settings = db.query(models.UserSettings).first()
        start_hour = user_settings.start_work_hour if user_settings else 9
        end_hour = user_settings.end_work_hour if user_settings else 18

        # Set schedule start: next working hour or tomorrow at start_hour if late
        now = datetime.datetime.now(timezone.utc).replace(tzinfo=None)
        start_time = now + timedelta(hours=1)
        if start_time.hour >= end_hour or start_time.hour < start_hour:
            roll_days = 1 if start_time.hour >= end_hour else 0
            start_time = datetime.datetime.combine(
                start_time.date() + timedelta(days=roll_days),
                datetime.time(start_hour, 0)
            )

        current_time = start_time
        replan_count = 0

        # Read risk config to check if we need emergency scheduling parameters (shorter breaks)
        config = db.query(models.RiskEngineConfig).first()
        critical_threshold = config.threshold_critical if config else 0.40

        for task in tasks:
            hours = task.estimated_hours if task.estimated_hours > 0 else 1.0
            
            # If critical risk, compress break slots (Shorter Pomodoros: 27m focus + 3m break)
            is_critical = task.completion_probability < critical_threshold
            focus_minutes = 27 if is_critical else 25
            break_minutes = 3 if is_critical else 5
            block_total_mins = focus_minutes + break_minutes

            num_blocks = int(hours * 60 / focus_minutes)
            if num_blocks == 0:
                num_blocks = 1

            for _ in range(num_blocks):
                # Resolve conflicts with Google Calendar events
                clash = True
                attempts = 0
                max_attempts = 100
                while clash and attempts < max_attempts:
                    clash = False
                    attempts += 1
                    block_end = current_time + timedelta(minutes=focus_minutes)
                    
                    for event in gcal_events:
                        ev_start = event.start_time
                        ev_end = event.end_time
                        
                        # Check overlap
                        if (current_time < ev_end) and (block_end > ev_start):
                            # Conflict detected! Push start time to after event end
                            current_time = ev_end + timedelta(minutes=5)
                            clash = True
                            replan_count += 1
                            break

                # Exceeded working hours? Roll over to next day
                if current_time.hour >= end_hour:
                    current_time = datetime.datetime.combine(
                        current_time.date() + timedelta(days=1),
                        datetime.time(start_hour, 0)
                    )
                    continue

                # Add focus block
                db_block = models.ScheduleBlock(
                    task_id=task.id,
                    start_time=current_time,
                    end_time=current_time + timedelta(minutes=focus_minutes),
                    is_focus_block=True
                )
                db.add(db_block)
                current_time += timedelta(minutes=block_total_mins)

        db.commit()
        if replan_count > 0:
            await AgentLogger.log_activity("Scheduler Agent", f"Automatically replanned calendar around {replan_count} external event conflicts.", db)


# --- 4. AI PREDICTION & RISK FORECASTING ENGINE ---
class AIPredictionEngine:
    @staticmethod
    async def run(task: models.Task, db: Session):
        await AgentLogger.log_activity("AI Prediction Engine", f"Forecasting completion probability for '{task.title}'", db)

        now = datetime.datetime.now(timezone.utc).replace(tzinfo=None)
        due_date = task.due_date
        if due_date.tzinfo is not None:
            due_date = due_date.astimezone(timezone.utc).replace(tzinfo=None)

        time_left = due_date - now
        total_hours_left = time_left.total_seconds() / 3600.0

        if total_hours_left <= 0:
            task.completion_probability = 0.0
            db.commit()
            return

        # Calculate user available hours in the remaining timeframe
        # Exclude sleep hours (approx 8 hrs per 24 hours)
        sleep_ratio = 8.0 / 24.0
        projected_sleep = total_hours_left * sleep_ratio

        # Gather external calendar events falling in this window
        gcal_events = db.query(models.CalendarEvent).filter(
            models.CalendarEvent.start_time >= now,
            models.CalendarEvent.end_time <= due_date
        ).all()
        meeting_hours = sum([(e.end_time - e.start_time).total_seconds() / 3600.0 for e in gcal_events])

        net_available_hours = total_hours_left - projected_sleep - meeting_hours
        if net_available_hours <= 0:
            net_available_hours = 0.1

        # Check AI Memory for procrastination factor
        delay_coefficient = 1.0
        memory_rec = db.query(models.AIMemory).filter(models.AIMemory.pattern_key == "procrastination_multiplier").first()
        if memory_rec:
            try:
                data = json.loads(memory_rec.pattern_data)
                delay_coefficient = data.get("multiplier", 1.2)
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.error(f"Error parsing procrastination multiplier from memory: {e}")

        required_hours = task.estimated_hours * delay_coefficient

        # Probability calculation
        ratio = net_available_hours / required_hours
        if ratio >= 1.2:
            prob = 0.95
        elif ratio <= 0.3:
            prob = 0.10
        else:
            # Linear scaling
            prob = 0.10 + (ratio - 0.3) * (0.85 / 0.9)
            prob = min(0.95, max(0.05, prob))

        # Boost probability based on subtask completion progress (up to +30%)
        # A task with 80% subtasks done is clearly closer to completion
        if task.subtasks:
            done = sum(1 for s in task.subtasks if s.is_completed)
            subtask_boost = (done / len(task.subtasks)) * 0.30
            prob = min(0.98, prob + subtask_boost)

        task.completion_probability = round(prob, 2)
        db.commit()
        
        await AgentLogger.log_activity("AI Prediction Engine", f"Completion probability for '{task.title}' is {int(prob * 100)}% (Net hours: {round(net_available_hours, 1)}h available vs {round(required_hours, 1)}h needed)", db)


# --- 5. RISK DETECTOR & RECOVERY DISPATCH ---
class RiskDetector:
    @staticmethod
    async def run(task: models.Task, db: Session):
        await AgentLogger.log_activity("Risk Detector", f"Scanning risk thresholds for '{task.title}'", db)

        # Get thresholds
        config = db.query(models.RiskEngineConfig).first()
        warning_thresh = config.threshold_warning if config else 0.70
        critical_thresh = config.threshold_critical if config else 0.40

        prob = task.completion_probability

        if prob < critical_thresh:
            await AgentLogger.log_activity("Risk Detector", f"⚠️ CRITICAL RISK detected for '{task.title}'! Activating emergency rescue and negotiations.", db)
            await RescueAgent.run(task, db)
            await NegotiationAgent.run(task, db)
            await MotivationAgent.trigger_alert(task, "critical", db)
        elif prob < warning_thresh:
            await AgentLogger.log_activity("Risk Detector", f"⚠️ WARNING state detected for '{task.title}'. Restructuring subtask priorities.", db)
            await RescueAgent.run(task, db)
            await MotivationAgent.trigger_alert(task, "warning", db)
        else:
            # Safe task
            task.rescue_strategy = None
            task.critical_next_action = "Maintain your current Pomodoro slots in the schedule."
            db.commit()


# --- 6. RESCUE AGENT ---
class RescueAgent:
    @staticmethod
    async def run(task: models.Task, db: Session, force: bool = False):
        if not force and task.rescue_strategy:
            # Plan already formulated, do not recreate
            return

        await AgentLogger.log_activity("Rescue Agent", f"Formulating Emergency Recovery Plan for '{task.title}'", db)

        # Gather task details
        system_prompt = (
            "You are the Emergency Rescue Agent. Formulate an action strategy for a task at risk of missing its deadline. "
            "Suggest how to prune scope, focus on minimum viable deliverables, and list a chronological micro-timeline. "
            "Return ONLY a JSON object containing: "
            "1. 'rescue_strategy' (string text explaining how to save the deadline) "
            "2. 'critical_next_action' (string detailing the single next vital step) "
            "3. 'timeline' (list of objects with 'time' (string, e.g. '6:30 PM') and 'title' (string task milestone))"
        )
        
        now_str = datetime.datetime.now(timezone.utc).strftime("%I:%M %p")
        user_prompt = f"Task: {task.title}\nDue: {task.due_date}\nProbability: {task.completion_probability}\nNow is: {now_str}"
        
        try:
            res = await call_llm(system_prompt, user_prompt, json_mode=True)
            cleaned = clean_json_text(res)
            data = json.loads(cleaned)

            task.rescue_strategy = data.get("rescue_strategy")
            task.critical_next_action = data.get("critical_next_action")
            task.rescue_timeline = json.dumps(data.get("timeline", []))
            
            # Shorten/prioritize remaining subtasks in database
            db.commit()
            await AgentLogger.log_activity("Rescue Agent", f"Recovery Plan written for '{task.title}'", db)
        except Exception as e:
            logger.error(f"Rescue Agent error: {e}")
            # Fallback algorithmic generator
            task.rescue_strategy = "Focus strictly on the minimum core requirements. Postpone formatting, polish, and documentation until after completion."
            task.critical_next_action = "Draft the core skeleton structure and submit initial placeholder blocks."
            
            # Simple timeline
            timeline = [
                {"time": "Start + 15m", "title": "Setup core skeleton structure", "completed": False},
                {"time": "Start + 45m", "title": "Write primary functional logic", "completed": False},
                {"time": "Start + 75m", "title": "Submit draft & upload baseline modules", "completed": False}
            ]
            task.rescue_timeline = json.dumps(timeline)
            db.commit()


# --- 7. NEGOTIATION AGENT ---
class NegotiationAgent:
    @staticmethod
    async def run(task: models.Task, db: Session, force: bool = False):
        if not force:
            # Check if draft already exists to avoid duplication
            existing = db.query(models.EmailDraft).filter(
                models.EmailDraft.task_id == task.id,
                models.EmailDraft.status == "Draft"
            ).first()

            if existing:
                return

        await AgentLogger.log_activity("Negotiation Agent", f"Drafting extension request email for '{task.title}'", db)

        system_prompt = (
            "You are the Negotiation Agent. Draft a professional, polite, and persuasive request for a deadline extension or meeting reschedule. "
            "Return ONLY a JSON object containing: "
            "1. 'recipient' (string, e.g. 'professor@university.edu', 'manager@company.com') "
            "2. 'subject' (string email subject) "
            "3. 'body' (string email body text with placeholders)"
        )
        user_prompt = f"Task: {task.title}\nDue: {task.due_date}\nProbability: {task.completion_probability}"

        try:
            res = await call_llm(system_prompt, user_prompt, json_mode=True)
            cleaned = clean_json_text(res)
            data = json.loads(cleaned)

            # Delete any existing draft before creating the new one if forcing
            if force:
                db.query(models.EmailDraft).filter(
                    models.EmailDraft.task_id == task.id,
                    models.EmailDraft.status == "Draft"
                ).delete()

            draft = models.EmailDraft(
                task_id=task.id,
                recipient=data.get("recipient", "stakeholder@organization.com"),
                subject=data.get("subject", f"Extension Request: {task.title}"),
                body=data.get("body", "Dear recipient,\n\nI am writing to request a brief extension..."),
                status="Draft"
            )
            db.add(draft)
            db.commit()
            await AgentLogger.log_activity("Negotiation Agent", f"Saved extension draft for '{task.title}' in the Negotiation Center.", db)
        except Exception as e:
            logger.error(f"Negotiation Agent error: {e}")
            # Fallback
            if force:
                db.query(models.EmailDraft).filter(
                    models.EmailDraft.task_id == task.id,
                    models.EmailDraft.status == "Draft"
                ).delete()
            draft = models.EmailDraft(
                task_id=task.id,
                recipient="stakeholder@company.com",
                subject=f"Reschedule & Update request: {task.title}",
                body=f"Dear Team,\n\nRegarding '{task.title}', I am tracking slightly behind on execution. To guarantee high quality, I would like to request an adjustment to our delivery target to tomorrow afternoon.\n\nThank you for understanding.",
                status="Draft"
            )
            db.add(draft)
            db.commit()


# --- 8. MOTIVATION AGENT ---
class MotivationAgent:
    @staticmethod
    async def trigger_alert(task: models.Task, level: str, db: Session):
        """
        Pushes a smart notification on state shifts.
        """
        msg = ""
        if level == "critical":
            msg = f"🚨 Action Needed: '{task.title}' completion probability is {int(task.completion_probability*100)}%. We drafted an extension email and activated emergency micro-schedules."
        else:
            msg = f"⚠️ Shift Alert: '{task.title}' is slipping. Starting Pomodoros now will guarantee submission."

        # Add notification
        notif = models.Notification(
            message=msg,
            type=level,
            is_read=False
        )
        db.add(notif)
        db.commit()
        await AgentLogger.log_activity("Motivation Agent", f"Dispatched smart notification alert: {msg[:60]}...", db)


# --- 9. REFLECTION AGENT (Self-Improving AI) ---
class ReflectionAgent:
    @staticmethod
    async def run(task: models.Task, db: Session):
        await AgentLogger.log_activity("Reflection Agent", f"Analyzing completion metrics for '{task.title}'", db)

        # Check estimate vs actual duration based on actual focus hours logged, or default to estimate
        actual_hours = task.actual_hours_spent
        if actual_hours <= 0.0:
            actual_hours = task.estimated_hours if task.estimated_hours > 0 else 0.5

        estimated = task.estimated_hours if task.estimated_hours > 0 else 0.5

        # Update procrastination multiplier pattern in AIMemory
        memory_rec = db.query(models.AIMemory).filter(models.AIMemory.pattern_key == "procrastination_multiplier").first()
        if not memory_rec:
            memory_rec = models.AIMemory(
                category="procrastination",
                pattern_key="procrastination_multiplier",
                pattern_data=json.dumps({"multiplier": 1.0, "completed_tasks_count": 0, "history": []})
            )
            db.add(memory_rec)
            db.commit()

        try:
            data = json.loads(memory_rec.pattern_data)
            history = data.get("history", [])
            count = data.get("completed_tasks_count", 0) + 1

            # Procrastination ratio: actual time vs estimated time
            ratio = actual_hours / estimated
            history.append(ratio)
            # Limit history
            if len(history) > 10:
                history.pop(0)

            # Average multiplier
            avg_mult = sum(history) / len(history)
            # Clip between 0.8 and 2.0 to avoid extreme prediction skewing
            avg_mult = min(2.0, max(0.8, avg_mult))

            data["multiplier"] = round(avg_mult, 2)
            data["completed_tasks_count"] = count
            data["history"] = history

            memory_rec.pattern_data = json.dumps(data)
            db.commit()

            await AgentLogger.log_activity(
                "Reflection Agent", 
                f"Successfully calculated multiplier factor: {round(ratio, 2)}x. Total memory dataset: {count} tasks. Adjusted coefficient to {round(avg_mult, 2)}x.", 
                db
            )
        except Exception as e:
            logger.error(f"Reflection Agent error: {e}")
