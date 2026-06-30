import json
import logging
import datetime
import asyncio
import re
from typing import List, Optional, Dict, Any
import httpx
import google.generativeai as genai
from pydantic import BaseModel, Field
from app.config import settings

logger = logging.getLogger(__name__)

# Configure Gemini as primary LLM (Google Technologies criterion)
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)


# ──────────────────────────────────────────────────────────────
# STRUCTURED OUTPUT SCHEMAS (Gemini native response_schema)
# ──────────────────────────────────────────────────────────────

class AISubtask(BaseModel):
    """Schema for a single subtask returned by the Planner / Decomposer agent."""
    title: str = Field(description="Actionable subtask description")
    estimated_minutes: int = Field(description="Duration estimate in minutes")

class TaskDecompositionResponse(BaseModel):
    """Schema for task decomposition output."""
    subtasks: List[AISubtask] = Field(description="List of 3-5 sequential subtasks")

class AIRescueResponse(BaseModel):
    """Schema for the Rescue Agent recovery plan."""
    rescue_strategy: str = Field(description="Strategic advice to prune scope and save deadline")
    critical_next_action: str = Field(description="The single next vital step to execute immediately")
    timeline: List[Dict[str, str]] = Field(description="Chronological milestones with keys 'time' and 'title'")

class AINegotiationResponse(BaseModel):
    """Schema for the Negotiation Agent email draft."""
    recipient: str = Field(description="Email recipient address")
    subject: str = Field(description="Email subject line")
    body: str = Field(description="Email body text")

class AIChatResponse(BaseModel):
    """Schema for the Chat Command Center responses."""
    response: str = Field(description="Conversational reply to the user")
    action_suggested: Optional[str] = Field(default=None, description="'create_task', 'rescue_task', 'suggest_schedule', or null")
    parsed_data: Optional[Dict[str, Any]] = Field(default=None, description="Extracted fields for the action")

class AIPrioritizationReasoning(BaseModel):
    """Schema for Prioritization Agent LLM reasoning."""
    ai_reasoning: str = Field(description="Explanation of why this task was prioritized over competing tasks")
    loss_if_skipped: str = Field(description="Consequence of postponing this task")
    reward: str = Field(description="Benefit of completing this task on time")

class AISchedulerInsight(BaseModel):
    """Schema for Scheduler Agent LLM insights."""
    scheduling_insight: str = Field(description="Summary of the scheduling plan and any conflicts detected")

class AIPredictionNarrative(BaseModel):
    """Schema for AI Prediction Engine LLM narrative."""
    prediction_narrative: str = Field(description="Natural language explanation of risk factors and completion probability")

class AIRiskAssessment(BaseModel):
    """Schema for Risk Detector LLM assessment."""
    risk_assessment: str = Field(description="Narrative explaining why this task is at critical/warning/safe risk level")

class AIMotivationMessage(BaseModel):
    """Schema for Motivation Agent LLM messages."""
    message: str = Field(description="Personalized, empathetic motivational message for the user")

class AIReflectionInsight(BaseModel):
    """Schema for Reflection Agent LLM insights."""
    insight: str = Field(description="Analysis of the user's work pattern and suggestions for improvement")
    adjusted_multiplier_suggestion: float = Field(description="Suggested procrastination multiplier between 0.8 and 2.0")


# ──────────────────────────────────────────────────────────────
# CORE LLM CALL FUNCTIONS
# ──────────────────────────────────────────────────────────────

def clean_json_text(text: str) -> str:
    """
    Cleans markdown wrappers and non-JSON prefixes/suffixes from the LLM output.
    Used only for Groq fallback path which doesn't support native structured outputs.
    """
    text = text.strip()

    # Try to find content within ```json and ``` or ``` and ```
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if match:
        return match.group(1).strip()

    # Otherwise, try to find the outermost [ ... ] or { ... } boundaries
    json_match = re.search(r'([\[{][\s\S]*[\]}])', text)
    if json_match:
        return json_match.group(1).strip()

    return text


async def call_llm_structured(system_prompt: str, user_prompt: str, response_schema: type) -> Any:
    """
    Structured LLM call using Gemini's native response_schema.
    Returns a parsed Python dict/list conforming to the schema.
    Falls back to Groq with manual parsing, then to heuristic.
    """
    # 1. Try Gemini with native Structured Outputs (PRIMARY — Google Technologies)
    if settings.GEMINI_API_KEY:
        try:
            generation_config = genai.GenerationConfig(
                temperature=0.2,
                response_mime_type="application/json",
                response_schema=response_schema
            )

            model = genai.GenerativeModel(
                model_name='gemini-2.5-flash',
                system_instruction=system_prompt,
                generation_config=generation_config
            )

            response = await asyncio.to_thread(
                model.generate_content,
                user_prompt
            )
            # Gemini guarantees schema conformance — parse directly
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Gemini structured call failed: {str(e)}")

    # 2. Groq fallback (manual JSON parsing)
    if settings.GROQ_API_KEY:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.2,
                "response_format": {"type": "json_object"}
            }

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    raw = data["choices"][0]["message"]["content"]
                    cleaned = clean_json_text(raw)
                    return json.loads(cleaned)
                else:
                    logger.error(f"Groq API error ({response.status_code}): {response.text}")
        except Exception as e:
            logger.error(f"Groq structured fallback failed: {str(e)}")

    # 3. Return None — caller handles heuristic fallback
    return None


async def call_llm(system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
    """
    Unified LLM call routing for plain-text or JSON responses.
    Priority: Google Gemini (primary) -> Groq (fallback) -> heuristic fallback.
    """
    # 1. Try Gemini API (PRIMARY — Google Technologies)
    if settings.GEMINI_API_KEY:
        try:
            generation_config = genai.GenerationConfig(temperature=0.2)
            if json_mode:
                generation_config = genai.GenerationConfig(
                    temperature=0.2,
                    response_mime_type="application/json"
                )

            model = genai.GenerativeModel(
                model_name='gemini-2.5-flash',
                system_instruction=system_prompt,
                generation_config=generation_config
            )

            response = await asyncio.to_thread(
                model.generate_content,
                user_prompt
            )
            return response.text
        except Exception as e:
            logger.error(f"Failed calling Gemini LLM: {str(e)}")

    # 2. Try Groq API (FALLBACK)
    if settings.GROQ_API_KEY:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.2
            }
            if json_mode:
                payload["response_format"] = {"type": "json_object"}

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    logger.error(f"Groq API error ({response.status_code}): {response.text}")
        except Exception as e:
            logger.error(f"Failed calling Groq LLM: {str(e)}")

    # 3. Heuristic Fallback
    logger.info("Using local heuristic fallback for LLM query.")
    return get_heuristic_fallback(system_prompt, user_prompt, json_mode)


def get_heuristic_fallback(system_prompt: str, user_prompt: str, json_mode: bool) -> str:
    """
    Intelligent local fallback generator to ensure full offline capability.
    """
    user_prompt_lower = user_prompt.lower()

    if json_mode:
        # Task Decomposer Heuristics
        if "decompose" in user_prompt_lower or "subtask" in user_prompt_lower:
            title = "Task"
            if "title:" in user_prompt_lower:
                idx = user_prompt_lower.find("title:")
                title = user_prompt[idx + 6:].split("\n")[0].strip()

            return json.dumps([
                {"title": f"Initial research and outlining for '{title}'", "estimated_minutes": 20},
                {"title": "Draft the core components and structure", "estimated_minutes": 45},
                {"title": "Review, edit, and check against requirements", "estimated_minutes": 15},
                {"title": "Final polish and submission check", "estimated_minutes": 10}
            ])

        # Chat parsing heuristics
        if "add" in user_prompt_lower or "create" in user_prompt_lower:
            title = "New AI Task"
            priority = "Medium"
            due_offset_days = 2

            if "priority" in user_prompt_lower:
                if "high" in user_prompt_lower:
                    priority = "High"
                elif "urgent" in user_prompt_lower:
                    priority = "Urgent"
                elif "low" in user_prompt_lower:
                    priority = "Low"

            due_date = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=due_offset_days)).strftime("%Y-%m-%dT18:00:00")

            return json.dumps({
                "response": f"I've prepared a task for you: '{title}' with {priority} priority, due by {due_date}. Click confirm to save it.",
                "action_suggested": "create_task",
                "parsed_data": {
                    "title": title,
                    "due_date": due_date,
                    "priority": priority,
                    "estimated_hours": 1.5,
                    "category": "Work"
                }
            })

        return json.dumps({
            "response": "I see you're working on something. Let me know how I can assist with scheduling, planning, or prioritizing your work.",
            "action_suggested": None,
            "parsed_data": None
        })
    else:
        if "rescue" in user_prompt_lower:
            return "I am activating the AI Emergency Rescue Protocol. I will break down your task, calculate the time budget, and slot focusing Pomodoro blocks into your calendar immediately."
        elif "help" in user_prompt_lower:
            return "I can help you prioritize near-deadline tasks, auto-generate detailed subtask breakdowns ('Rescue Plan'), schedule focus blocks, and chat via voice or text. Try typing 'Add a task to submit report by tomorrow'."
        return "I've analyzed your productivity status. To maximize efficiency, try breaking down your upcoming high-panic tasks and setting up a dedicated Pomodoro focus timer."


# ──────────────────────────────────────────────────────────────
# EXTERNAL FACING APIs (used by routes)
# ──────────────────────────────────────────────────────────────

async def decompose_task_ai(title: str, description: str) -> List[Dict[str, Any]]:
    system_prompt = (
        "You are an expert AI task breakdown agent. Your goal is to split a complex task into a set of 3 to 5 smaller, "
        "completely actionable, sequential sub-tasks. Each sub-task should have a clear title and a realistic duration estimate."
    )
    user_prompt = f"Decompose this task:\nTitle: {title}\nDescription: {description}"

    # Try structured output first
    result = await call_llm_structured(system_prompt, user_prompt, TaskDecompositionResponse)
    if result and "subtasks" in result:
        formatted = []
        for i, sub in enumerate(result["subtasks"]):
            formatted.append({
                "title": sub.get("title", f"Action Item {i+1}"),
                "estimated_minutes": int(sub.get("estimated_minutes", 30)),
                "order": i
            })
        return formatted

    # Fallback: try legacy call_llm
    subtasks = []
    try:
        response_text = await call_llm(system_prompt, user_prompt, json_mode=True)
        cleaned_text = clean_json_text(response_text)
        subtasks = json.loads(cleaned_text)
    except Exception as e:
        logger.error(f"Error in decompose_task_ai parsing: {str(e)}")
        try:
            subtasks = json.loads(get_heuristic_fallback(system_prompt, user_prompt, json_mode=True))
        except Exception as fallback_err:
            logger.error(f"Failed parsing fallback heuristic: {str(fallback_err)}")
            subtasks = []

    if not isinstance(subtasks, list):
        subtasks = []

    formatted = []
    for i, sub in enumerate(subtasks):
        formatted.append({
            "title": sub.get("title", f"Action Item {i+1}"),
            "estimated_minutes": int(sub.get("estimated_minutes", 30)),
            "order": sub.get("order", i)
        })
    return formatted


async def process_chat_message(
    message: str,
    history: List[Dict[str, Any]],
    active_tasks_context: str = ""
) -> Dict[str, Any]:
    system_prompt = (
        "You are the core intelligence of 'The Last-Minute Life Saver' productivity tool. "
        "You help users manage tasks, prioritize their time, and survive tight deadlines. "
        "You must analyze the user message. If they express a clear desire to create a task, "
        "extract the parameters (title, due_date in YYYY-MM-DDTHH:MM:SS format, priority as Low, Medium, High, or Urgent, estimated_hours as a float, category). "
        "If they want to rescue a task (break down or schedule), set action_suggested to 'rescue_task' and parse the task name/ID. "
        "For simple conversations or advice, return a helpful, motivating text response. "
        "Always return a JSON object with: "
        "1. 'response' (string of your conversational reply) "
        "2. 'action_suggested' (string or null: 'create_task', 'rescue_task', 'suggest_schedule') "
        "3. 'parsed_data' (object or null, containing extracted fields for the action: e.g. for create_task: "
        "{'title': '...', 'due_date': '...', 'priority': '...', 'estimated_hours': 1.5, 'category': '...'})"
    )

    # Formulate context from history (last 5 messages)
    history_context = ""
    for msg in history[-5:]:
        history_context += f"{msg.get('sender', 'user')}: {msg.get('text', '')}\n"

    # Inject active task context so the AI knows what the user is working on
    task_context_block = ""
    if active_tasks_context:
        task_context_block = f"\n\nUser's Active Tasks:\n{active_tasks_context}\n"

    user_prompt = f"History:\n{history_context}{task_context_block}\nUser: {message}"

    # Try structured output first
    result = await call_llm_structured(system_prompt, user_prompt, AIChatResponse)
    if result:
        return {
            "response": result.get("response", "I've processed your message."),
            "action_suggested": result.get("action_suggested"),
            "parsed_data": result.get("parsed_data")
        }

    # Fallback: legacy call
    try:
        response_text = await call_llm(system_prompt, user_prompt, json_mode=True)
        cleaned_text = clean_json_text(response_text)
        result = json.loads(cleaned_text)
        return {
            "response": result.get("response", "I've processed your message."),
            "action_suggested": result.get("action_suggested"),
            "parsed_data": result.get("parsed_data")
        }
    except Exception as e:
        logger.error(f"Error in process_chat_message parsing: {str(e)}")

    return {
        "response": "I understand you need assistance. Let me help you set up or schedule a task to stay on track.",
        "action_suggested": None,
        "parsed_data": None
    }


async def generate_behavioral_recommendations(
    completed_count: int,
    overdue_count: int,
    streaks: List[Dict[str, Any]]
) -> List[str]:
    """
    Generates dynamic productivity insights/tips.
    """
    system_prompt = (
        "You are an elite productivity coach. Based on the user's weekly metrics, "
        "generate 2 to 3 highly tailored, positive, actionable recommendations. "
        "Return ONLY a JSON array of strings. Do not include markdown codeblocks."
    )

    streaks_str = ", ".join([f"{s['title']}: Streak {s['streak']} days" for s in streaks])
    user_prompt = (
        f"Completed Tasks: {completed_count}, "
        f"Overdue Tasks: {overdue_count}, "
        f"Habits and Streaks: {streaks_str}. "
        f"Generate personalized productivity recommendations."
    )

    try:
        response_text = await call_llm(system_prompt, user_prompt, json_mode=True)
        cleaned_text = clean_json_text(response_text)
        tips = json.loads(cleaned_text)
        if isinstance(tips, list):
            return tips
    except Exception as e:
        logger.error(f"Error generating recommendations: {str(e)}")

    return [
        "Create micro-deadlines by splitting your next Urgent task into 3 sub-tasks.",
        "Strengthen your habits! Slot in a habit log right after a work task for natural reinforcement.",
        "Buffer time: We recommend setting your deadlines 2 hours earlier to absorb unexpected delays."
    ]
