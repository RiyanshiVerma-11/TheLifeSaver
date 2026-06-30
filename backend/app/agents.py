import json
import logging
import datetime
from datetime import timedelta, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app import models, schemas
from app.ai_agent import (
    call_llm, call_llm_structured, clean_json_text,
    AIPrioritizationReasoning, AISchedulerInsight,
    AIPredictionNarrative, AIRiskAssessment, AIMotivationMessage,
    AIReflectionInsight, AIRescueResponse, AINegotiationResponse
)

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

            # 2. Prioritization Agent (LLM-enhanced reasoning)
            await PrioritizationAgent.run(db)

            # 3. Scheduler Agent (LLM scheduling insights)
            await SchedulerAgent.run(db)

            # 4. AI Prediction & Risk Forecasting Engine (LLM prediction narrative)
            if task:
                await AIPredictionEngine.run(task, db)
            else:
                active_tasks = db.query(models.Task).filter(models.Task.status != models.StatusEnum.COMPLETED).all()
                for t in active_tasks:
                    await AIPredictionEngine.run(t, db)

            # 5. Risk Detector Agent (LLM risk assessment)
            if task:
                await RiskDetector.run(task, db)
            else:
                active_tasks = db.query(models.Task).filter(models.Task.status != models.StatusEnum.COMPLETED).all()
                for t in active_tasks:
                    await RiskDetector.run(t, db)

            # 6. Reflection Agent (LLM completion insights)
            if event_type == "task_completed" and task:
                await ReflectionAgent.run(task, db)

            # Refresh task state
            if task:
                db.refresh(task)
            
            await AgentLogger.log_activity("Orchestrator", "Multi-Agent pipeline executed successfully.", db)
        except Exception as e:
            logger.error(f"Pipeline Execution Error: {str(e)}")
            await AgentLogger.log_activity("Orchestrator", f"Pipeline encountered error: {str(e)[:100]}", db)


# --- 1. PLANNER AGENT (LLM-powered task decomposition) ---
class PlannerAgent:
    @staticmethod
    async def run(task: models.Task, db: Session):
        await AgentLogger.log_activity("Planner Agent", f"Planning task outline for '{task.title}'", db)
        # Check if subtasks already exist. If not, auto-generate.
        if not task.subtasks:
            system_prompt = (
                "You are an expert AI task planner. Break down the user's task into 3 to 5 actionable subtasks. "
                "Each subtask must have a clear title and estimated_minutes (integer)."
            )
            user_prompt = f"Task: {task.title}\nDescription: {task.description or ''}"
            
            try:
                # Try Gemini Structured Outputs first
                from app.ai_agent import TaskDecompositionResponse
                result = await call_llm_structured(system_prompt, user_prompt, TaskDecompositionResponse)
                
                subtasks_data = []
                if result and "subtasks" in result:
                    subtasks_data = result["subtasks"]
                else:
                    # Fallback to legacy call
                    res = await call_llm(system_prompt, user_prompt, json_mode=True)
                    cleaned = clean_json_text(res)
                    subtasks_data = json.loads(cleaned)

                for i, sub in enumerate(subtasks_data):
                    db_sub = models.SubTask(
                        task_id=task.id,
                        title=sub.get("title", f"Subtask {i+1}"),
                        is_completed=False,
                        estimated_minutes=int(sub.get("estimated_minutes", 30)),
                        order=i
                    )
                    db.add(db_sub)
                db.commit()
                await AgentLogger.log_activity("Planner Agent", f"Generated {len(subtasks_data)} AI checklists for '{task.title}'", db)
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


# --- 2. PRIORITIZATION AGENT (LLM-enhanced AI reasoning) ---
class PrioritizationAgent:
    @staticmethod
    async def run(db: Session):
        await AgentLogger.log_activity("Prioritization Agent", "Evaluating task priorities and computing Panic Indices.", db)
        
        tasks = db.query(models.Task).filter(models.Task.status != models.StatusEnum.COMPLETED).all()
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

        # Update panic indices first (algorithmic core — always runs)
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
                task.panic_index = round(min((task.estimated_hours / max(hours_left, 0.1)) * mult, 20.0), 3)
            
        db.commit()

        # Sort by panic index for opportunity cost analysis
        active_tasks = sorted(tasks, key=lambda t: t.panic_index, reverse=True)

        # LLM-enhanced reasoning for top tasks
        if len(active_tasks) > 1:
            for idx, task in enumerate(active_tasks):
                next_tasks = active_tasks[idx+1:]
                competing = next_tasks[0] if next_tasks else None
                
                # Set defaults first (algorithmic fallback)
                task.impact = "High" if task.priority in [models.PriorityEnum.URGENT, models.PriorityEnum.HIGH] else "Medium"
                
                # Call LLM for dynamic reasoning
                try:
                    competing_ctx = f"Competing task: '{competing.title}' (Panic: {competing.panic_index})" if competing else "No competing tasks."
                    system_prompt = (
                        "You are the Prioritization Agent in a productivity system. Explain concisely why this task should be prioritized, "
                        "what the user loses if they skip it, and what reward they gain by completing it on time. "
                        "Be specific, quantitative, and motivating. Keep each field under 2 sentences."
                    )
                    user_prompt = (
                        f"Task: '{task.title}' (Category: {task.category}, Priority: {task.priority.value}, "
                        f"Panic Score: {task.panic_index}, Hours Estimated: {task.estimated_hours}h)\n"
                        f"{competing_ctx}"
                    )

                    result = await call_llm_structured(system_prompt, user_prompt, AIPrioritizationReasoning)
                    if result:
                        task.ai_reasoning = result.get("ai_reasoning", task.ai_reasoning)
                        task.loss_if_skipped = result.get("loss_if_skipped", task.loss_if_skipped)
                        task.reward = result.get("reward", task.reward)
                    else:
                        # Heuristic fallback
                        task.reward = f"Complete critical deliverable '{task.title}' and maintain progress streak."
                        task.loss_if_skipped = f"Delaying this will force '{competing.title if competing else 'subsequent tasks'}' to slide, increasing stress probability."
                        task.ai_reasoning = (
                            f"Prioritized '{task.title}' (Panic Score: {task.panic_index}) over "
                            f"'{competing.title if competing else 'N/A'}' based on remaining time vs estimated effort."
                        )
                except Exception as e:
                    logger.error(f"Prioritization LLM reasoning error: {e}")
                    task.reward = f"Complete critical deliverable '{task.title}' and maintain progress streak."
                    task.loss_if_skipped = f"Delaying this will force subsequent tasks to slide, increasing stress probability."
                    task.ai_reasoning = f"Prioritized '{task.title}' (Panic Score: {task.panic_index}) based on remaining time vs estimated effort."

        elif active_tasks:
            task = active_tasks[0]
            task.impact = "High" if task.priority == models.PriorityEnum.URGENT else "Medium"
            task.reward = "Fulfill upcoming task milestone."
            task.loss_if_skipped = "Forfeit streak progress."
            task.ai_reasoning = "Only active task in focus window. Initializing immediate execution block."

        db.commit()


# --- 3. SCHEDULER AGENT (LLM scheduling insights) ---
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

        # Clear old focus blocks and remove from Google Calendar if connected
        old_blocks = db.query(models.ScheduleBlock).all()
        user_settings = db.query(models.UserSettings).first()
        refresh_token = user_settings.google_refresh_token_id if user_settings else None

        if refresh_token:
            try:
                from app.google_services import GoogleCalendarClient
                gcal_client = GoogleCalendarClient(refresh_token)
                if gcal_client.is_connected():
                    for ob in old_blocks:
                        if ob.gcal_event_id:
                            gcal_client.delete_event(ob.gcal_event_id)
            except Exception as e:
                logger.error(f"Error cleaning up old Google Calendar events: {e}")

        db.query(models.ScheduleBlock).delete()
        db.commit()

        # Retrieve user configured work hours from settings (default to 9 AM to 6 PM)
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
        total_blocks = 0

        # Read risk config to check if we need emergency scheduling parameters
        config = db.query(models.RiskEngineConfig).first()
        critical_threshold = config.threshold_critical if config else 0.40

        for task in tasks:
            hours = task.estimated_hours if task.estimated_hours > 0 else 1.0
            
            # If critical risk, compress break slots
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

                # Add focus block to Google Calendar if connected
                gcal_id = None
                if refresh_token:
                    try:
                        from app.google_services import GoogleCalendarClient
                        gcal_client = GoogleCalendarClient(refresh_token)
                        if gcal_client.is_connected():
                            start_iso = current_time.isoformat() + "Z"
                            end_iso = (current_time + timedelta(minutes=focus_minutes)).isoformat() + "Z"
                            summary = f"Focus Block: {task.title}"
                            description = "AI Scheduled Pomodoro Focus Block created by LMLS"
                            gcal_id = gcal_client.create_event(summary, start_iso, end_iso, description)
                    except Exception as e:
                        logger.error(f"Error creating Google Calendar event for focus block: {e}")

                db_block = models.ScheduleBlock(
                    task_id=task.id,
                    start_time=current_time,
                    end_time=current_time + timedelta(minutes=focus_minutes),
                    is_focus_block=True,
                    gcal_event_id=gcal_id
                )
                db.add(db_block)
                current_time += timedelta(minutes=block_total_mins)
                total_blocks += 1

        db.commit()

        # LLM scheduling insight
        try:
            conflict_names = [e.title for e in gcal_events]
            task_names = [t.title for t in tasks[:5]]
            system_prompt = (
                "You are the Scheduler Agent. Summarize the scheduling plan you just created in 1-2 sentences. "
                "Mention how many focus blocks were created, any calendar conflicts detected, and the overall strategy."
            )
            user_prompt = (
                f"Scheduled {total_blocks} Pomodoro focus blocks across {len(tasks)} tasks.\n"
                f"Calendar conflicts resolved: {replan_count} (Events: {', '.join(conflict_names) if conflict_names else 'None'}).\n"
                f"Tasks scheduled: {', '.join(task_names)}.\n"
                f"Work hours: {start_hour}:00 to {end_hour}:00."
            )

            result = await call_llm_structured(system_prompt, user_prompt, AISchedulerInsight)
            if result:
                insight = result.get("scheduling_insight", "")
                await AgentLogger.log_activity("Scheduler Agent", f"AI Insight: {insight}", db)
            elif replan_count > 0:
                await AgentLogger.log_activity("Scheduler Agent", f"Automatically replanned calendar around {replan_count} external event conflicts.", db)
        except Exception as e:
            logger.error(f"Scheduler LLM insight error: {e}")
            if replan_count > 0:
                await AgentLogger.log_activity("Scheduler Agent", f"Automatically replanned calendar around {replan_count} external event conflicts.", db)


# --- 4. AI PREDICTION & RISK FORECASTING ENGINE (LLM prediction narrative) ---
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

        # Check AI Memory for procrastination factor (category-aware)
        delay_coefficient = 1.0
        memory_rec = db.query(models.AIMemory).filter(models.AIMemory.pattern_key == "procrastination_multiplier").first()
        if memory_rec:
            try:
                data = json.loads(memory_rec.pattern_data)
                # Category-aware multiplier
                category = task.category or "Work"
                cat_mults = data.get("category_multipliers", {})
                if category in cat_mults and len(cat_mults[category]) > 0:
                    delay_coefficient = sum(cat_mults[category]) / len(cat_mults[category])
                else:
                    delay_coefficient = data.get("multiplier", 1.2)
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.error(f"Error parsing procrastination multiplier from memory: {e}")

        required_hours = task.estimated_hours * delay_coefficient

        # Probability calculation (algorithmic core)
        ratio = net_available_hours / required_hours
        if ratio >= 1.2:
            prob = 0.95
        elif ratio <= 0.3:
            prob = 0.10
        else:
            prob = 0.10 + (ratio - 0.3) * (0.85 / 0.9)
            prob = min(0.95, max(0.05, prob))

        # Boost probability based on subtask completion progress (up to +30%)
        if task.subtasks:
            done = sum(1 for s in task.subtasks if s.is_completed)
            subtask_boost = (done / len(task.subtasks)) * 0.30
            prob = min(0.98, prob + subtask_boost)

        task.completion_probability = round(prob, 2)
        db.commit()
        
        # LLM prediction narrative
        try:
            system_prompt = (
                "You are the AI Prediction Engine. Explain in 1-2 sentences why this task has the given completion probability. "
                "Mention specific risk factors like time left, meeting conflicts, procrastination history, or subtask progress."
            )
            user_prompt = (
                f"Task: '{task.title}' (Category: {task.category})\n"
                f"Completion Probability: {int(prob * 100)}%\n"
                f"Net available hours: {round(net_available_hours, 1)}h, Required: {round(required_hours, 1)}h\n"
                f"Meeting conflicts: {round(meeting_hours, 1)}h, Procrastination coefficient: {round(delay_coefficient, 2)}x\n"
                f"Subtask progress: {sum(1 for s in task.subtasks if s.is_completed)}/{len(task.subtasks)} done" if task.subtasks else ""
            )

            result = await call_llm_structured(system_prompt, user_prompt, AIPredictionNarrative)
            if result:
                narrative = result.get("prediction_narrative", "")
                await AgentLogger.log_activity(
                    "AI Prediction Engine",
                    f"Completion probability for '{task.title}' is {int(prob * 100)}%. {narrative}",
                    db
                )
            else:
                await AgentLogger.log_activity(
                    "AI Prediction Engine",
                    f"Completion probability for '{task.title}' is {int(prob * 100)}% (Net hours: {round(net_available_hours, 1)}h available vs {round(required_hours, 1)}h needed)",
                    db
                )
        except Exception as e:
            logger.error(f"Prediction LLM narrative error: {e}")
            await AgentLogger.log_activity(
                "AI Prediction Engine",
                f"Completion probability for '{task.title}' is {int(prob * 100)}% (Net hours: {round(net_available_hours, 1)}h available vs {round(required_hours, 1)}h needed)",
                db
            )


# --- 5. RISK DETECTOR & RECOVERY DISPATCH (LLM risk assessment) ---
class RiskDetector:
    @staticmethod
    async def run(task: models.Task, db: Session):
        await AgentLogger.log_activity("Risk Detector", f"Scanning risk thresholds for '{task.title}'", db)

        # Get thresholds
        config = db.query(models.RiskEngineConfig).first()
        warning_thresh = config.threshold_warning if config else 0.70
        critical_thresh = config.threshold_critical if config else 0.40

        prob = task.completion_probability

        # LLM risk assessment
        risk_level = "safe"
        if prob < critical_thresh:
            risk_level = "critical"
        elif prob < warning_thresh:
            risk_level = "warning"

        try:
            system_prompt = (
                "You are the Risk Detector agent. Classify this task's risk level and explain in 1 sentence "
                "why it's at this risk level. Be specific about the factors (time pressure, probability, priority)."
            )
            user_prompt = (
                f"Task: '{task.title}'\n"
                f"Completion Probability: {int(prob * 100)}%\n"
                f"Panic Index: {task.panic_index}\n"
                f"Priority: {task.priority.value}\n"
                f"Risk Level: {risk_level.upper()}\n"
                f"Thresholds: Critical < {int(critical_thresh * 100)}%, Warning < {int(warning_thresh * 100)}%"
            )

            result = await call_llm_structured(system_prompt, user_prompt, AIRiskAssessment)
            if result:
                assessment = result.get("risk_assessment", "")
                await AgentLogger.log_activity("Risk Detector", f"Assessment for '{task.title}': {assessment}", db)
        except Exception as e:
            logger.error(f"Risk Detector LLM error: {e}")

        # Dispatch based on risk level
        if risk_level == "critical":
            await AgentLogger.log_activity("Risk Detector", f"⚠️ CRITICAL RISK detected for '{task.title}'! Activating emergency rescue and negotiations.", db)
            await RescueAgent.run(task, db)
            await NegotiationAgent.run(task, db)
            await MotivationAgent.trigger_alert(task, "critical", db)
        elif risk_level == "warning":
            await AgentLogger.log_activity("Risk Detector", f"⚠️ WARNING state detected for '{task.title}'. Restructuring subtask priorities.", db)
            await RescueAgent.run(task, db)
            await MotivationAgent.trigger_alert(task, "warning", db)
        else:
            # Safe task
            task.rescue_strategy = None
            task.critical_next_action = "Maintain your current Pomodoro slots in the schedule."
            db.commit()


# --- 6. RESCUE AGENT (LLM-powered with structured output) ---
class RescueAgent:
    @staticmethod
    async def run(task: models.Task, db: Session, force: bool = False):
        if not force and task.rescue_strategy:
            return

        await AgentLogger.log_activity("Rescue Agent", f"Formulating Emergency Recovery Plan for '{task.title}'", db)

        system_prompt = (
            "You are the Emergency Rescue Agent. Formulate an action strategy for a task at risk of missing its deadline. "
            "Suggest how to prune scope, focus on minimum viable deliverables, and list a chronological micro-timeline. "
            "The rescue_strategy should be a concise 2-3 sentence recovery plan. "
            "The critical_next_action should be the single most important step to do right now. "
            "The timeline should have 3-5 milestones with realistic times."
        )
        
        now_str = datetime.datetime.now(timezone.utc).strftime("%I:%M %p")
        user_prompt = f"Task: {task.title}\nDue: {task.due_date}\nProbability: {task.completion_probability}\nNow is: {now_str}"
        
        try:
            # Try Gemini Structured Outputs
            result = await call_llm_structured(system_prompt, user_prompt, AIRescueResponse)
            
            if result:
                task.rescue_strategy = result.get("rescue_strategy")
                task.critical_next_action = result.get("critical_next_action")
                task.rescue_timeline = json.dumps(result.get("timeline", []))
                db.commit()
                await AgentLogger.log_activity("Rescue Agent", f"AI Recovery Plan written for '{task.title}'", db)
                return

            # Fallback: legacy call
            res = await call_llm(system_prompt, user_prompt, json_mode=True)
            cleaned = clean_json_text(res)
            data = json.loads(cleaned)

            task.rescue_strategy = data.get("rescue_strategy")
            task.critical_next_action = data.get("critical_next_action")
            task.rescue_timeline = json.dumps(data.get("timeline", []))
            db.commit()
            await AgentLogger.log_activity("Rescue Agent", f"Recovery Plan written for '{task.title}'", db)
        except Exception as e:
            logger.error(f"Rescue Agent error: {e}")
            # Fallback algorithmic generator
            task.rescue_strategy = "Focus strictly on the minimum core requirements. Postpone formatting, polish, and documentation until after completion."
            task.critical_next_action = "Draft the core skeleton structure and submit initial placeholder blocks."
            
            timeline = [
                {"time": "Start + 15m", "title": "Setup core skeleton structure", "completed": False},
                {"time": "Start + 45m", "title": "Write primary functional logic", "completed": False},
                {"time": "Start + 75m", "title": "Submit draft & upload baseline modules", "completed": False}
            ]
            task.rescue_timeline = json.dumps(timeline)
            db.commit()


# --- 7. NEGOTIATION AGENT (LLM-powered with structured output) ---
class NegotiationAgent:
    @staticmethod
    async def run(task: models.Task, db: Session, force: bool = False):
        if not force:
            existing = db.query(models.EmailDraft).filter(
                models.EmailDraft.task_id == task.id,
                models.EmailDraft.status == "Draft"
            ).first()
            if existing:
                return

        await AgentLogger.log_activity("Negotiation Agent", f"Drafting extension request email for '{task.title}'", db)

        system_prompt = (
            "You are the Negotiation Agent. Draft a professional, polite, and persuasive request for a deadline extension or meeting reschedule. "
            "Include a realistic recipient email, a clear subject line, and a body with placeholders for names."
        )
        user_prompt = f"Task: {task.title}\nDue: {task.due_date}\nProbability: {task.completion_probability}"

        try:
            # Try Gemini Structured Outputs
            result = await call_llm_structured(system_prompt, user_prompt, AINegotiationResponse)
            
            if result:
                if force:
                    db.query(models.EmailDraft).filter(
                        models.EmailDraft.task_id == task.id,
                        models.EmailDraft.status == "Draft"
                    ).delete()

                draft = models.EmailDraft(
                    task_id=task.id,
                    recipient=result.get("recipient", "stakeholder@organization.com"),
                    subject=result.get("subject", f"Extension Request: {task.title}"),
                    body=result.get("body", "Dear recipient,\n\nI am writing to request a brief extension..."),
                    status="Draft"
                )
                db.add(draft)
                db.commit()
                await AgentLogger.log_activity("Negotiation Agent", f"Saved AI-generated extension draft for '{task.title}' in the Negotiation Center.", db)
                return

            # Fallback: legacy call
            res = await call_llm(system_prompt, user_prompt, json_mode=True)
            cleaned = clean_json_text(res)
            data = json.loads(cleaned)

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


# --- 8. MOTIVATION AGENT (LLM-powered personalized messages) ---
class MotivationAgent:
    @staticmethod
    async def trigger_alert(task: models.Task, level: str, db: Session):
        """
        Pushes a smart notification on state shifts — now with LLM-personalized messages.
        """
        msg = ""

        # Try LLM-generated motivational message
        try:
            system_prompt = (
                "You are the Motivation Agent in a productivity tool. Generate a single empathetic, action-oriented "
                "motivational notification message for the user. Be specific to their task and situation. "
                "Include an emoji at the start. Keep it under 2 sentences."
            )
            user_prompt = (
                f"Task: '{task.title}'\n"
                f"Risk Level: {level}\n"
                f"Completion Probability: {int(task.completion_probability * 100)}%\n"
                f"Panic Index: {task.panic_index}\n"
                f"Category: {task.category}"
            )

            result = await call_llm_structured(system_prompt, user_prompt, AIMotivationMessage)
            if result:
                msg = result.get("message", "")
        except Exception as e:
            logger.error(f"Motivation Agent LLM error: {e}")

        # Fallback if LLM didn't produce a message
        if not msg:
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
        await AgentLogger.log_activity("Motivation Agent", f"Dispatched AI-personalized notification: {msg[:80]}...", db)


# --- 9. REFLECTION AGENT (Self-Improving AI with LLM insights) ---
class ReflectionAgent:
    @staticmethod
    async def run(task: models.Task, db: Session):
        await AgentLogger.log_activity("Reflection Agent", f"Analyzing completion metrics for '{task.title}'", db)

        # Check estimate vs actual duration
        actual_hours = task.actual_hours_spent
        if actual_hours <= 0.0:
            actual_hours = task.estimated_hours if task.estimated_hours > 0 else 0.5

        estimated = task.estimated_hours if task.estimated_hours > 0 else 0.5
        ratio = actual_hours / estimated
        category = task.category or "Work"

        # Update procrastination multiplier pattern in AIMemory (category-aware)
        memory_rec = db.query(models.AIMemory).filter(models.AIMemory.pattern_key == "procrastination_multiplier").first()
        if not memory_rec:
            memory_rec = models.AIMemory(
                category="procrastination",
                pattern_key="procrastination_multiplier",
                pattern_data=json.dumps({"multiplier": 1.0, "completed_tasks_count": 0, "history": [], "category_multipliers": {}})
            )
            db.add(memory_rec)
            db.commit()

        try:
            data = json.loads(memory_rec.pattern_data)
            history = data.get("history", [])
            count = data.get("completed_tasks_count", 0) + 1
            cat_mults = data.get("category_multipliers", {})

            # Global history
            history.append(ratio)
            if len(history) > 10:
                history.pop(0)

            # Category-specific history
            if category not in cat_mults:
                cat_mults[category] = []
            cat_mults[category].append(ratio)
            if len(cat_mults[category]) > 10:
                cat_mults[category].pop(0)

            # Average multiplier (global)
            avg_mult = sum(history) / len(history)
            avg_mult = min(2.0, max(0.8, avg_mult))

            data["multiplier"] = round(avg_mult, 2)
            data["completed_tasks_count"] = count
            data["history"] = history
            data["category_multipliers"] = cat_mults

            memory_rec.pattern_data = json.dumps(data)
            db.commit()

            # LLM reflection insight
            try:
                cat_avg = sum(cat_mults[category]) / len(cat_mults[category]) if cat_mults.get(category) else 1.0
                system_prompt = (
                    "You are the Reflection Agent in a self-improving productivity system. Analyze the user's task completion pattern "
                    "and generate a brief insight about their work habits. Suggest a procrastination multiplier adjustment. "
                    "Be encouraging but honest. Keep the insight under 2 sentences."
                )
                user_prompt = (
                    f"Task completed: '{task.title}' (Category: {category})\n"
                    f"Estimated: {estimated}h, Actual: {actual_hours}h (Ratio: {round(ratio, 2)}x)\n"
                    f"Global procrastination multiplier: {round(avg_mult, 2)}x\n"
                    f"Category '{category}' average ratio: {round(cat_avg, 2)}x\n"
                    f"Total tasks analyzed: {count}"
                )

                result = await call_llm_structured(system_prompt, user_prompt, AIReflectionInsight)
                if result:
                    insight = result.get("insight", "")
                    suggested_mult = result.get("adjusted_multiplier_suggestion", avg_mult)
                    suggested_mult = min(2.0, max(0.8, suggested_mult))
                    
                    await AgentLogger.log_activity(
                        "Reflection Agent",
                        f"AI Insight: {insight} (Suggested multiplier: {round(suggested_mult, 2)}x)",
                        db
                    )
                else:
                    await AgentLogger.log_activity(
                        "Reflection Agent",
                        f"Calculated multiplier factor: {round(ratio, 2)}x. Total memory dataset: {count} tasks. Adjusted coefficient to {round(avg_mult, 2)}x.",
                        db
                    )
            except Exception as e:
                logger.error(f"Reflection LLM insight error: {e}")
                await AgentLogger.log_activity(
                    "Reflection Agent",
                    f"Calculated multiplier factor: {round(ratio, 2)}x. Total memory dataset: {count} tasks. Adjusted coefficient to {round(avg_mult, 2)}x.",
                    db
                )
        except Exception as e:
            logger.error(f"Reflection Agent error: {e}")
