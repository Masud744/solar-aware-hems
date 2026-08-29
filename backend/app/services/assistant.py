# Groq LLM Assistant Service for Solar-Integrated HEMS (SolarMate AI)
import json
import logging
import uuid
from typing import Dict, Any, List, Optional
from groq import Groq

from app.config import settings
from app.database import get_supabase
from app.services.assistant_tools import (
    HEMS_TOOLS_SCHEMA,
    execute_tool_call,
    get_dhaka_now,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are SolarMate AI, the AI-powered Conversational Assistant for the research project 'Risk-Aware and Explainable AI for Solar-Integrated Residential Energy Management Under Forecast Uncertainty: An IoT-Enabled Framework' (Solar-Aware HEMS) deployed in Kaliakair, Gazipur, Bangladesh (Asia/Dhaka timezone, BST = UTC+6).

Your purpose is to answer questions, explain energy and forecasts, evaluate appliance run safety, recommend optimal solar scheduling windows, and provide energy accounting updates based on REAL backend data.

================================================================================
CRITICAL OPERATIONAL & SAFETY RULES:
================================================================================

1. STRICT HARDWARE SAFETY RESTRICTION (NEVER DIRECTLY ACTUATE HARDWARE):
   - You are strictly an INFORMATION, FORECASTING, AND ADVISORY ASSISTANT.
   - You DO NOT have the capability or authority to switch physical relays, toggle switches, or actuate hardware.
   - If the user asks you to physically switch or turn on/off any relay or appliance (e.g., "turn on the heater", "turn off relay 1", "switch my pump to solar"), you MUST politely decline and explain that physical relay switching is restricted to the manual controls on the Appliances dashboard page for electrical safety.

2. NEVER FABRICATE OR HALLUCINATE SENSOR OR FORECAST NUMBERS:
   - When asked about live telemetry (temperature, humidity, power, voltage, relay state) or ML predictions (solar, load, safe surplus, energy used), ALWAYS invoke the corresponding tool.
   - If a reading is unavailable or a tool returns an error, state honestly that the sensor reading or forecast is currently unavailable. Never invent plausible numbers.

3. DATA PROVENANCE HONESTY:
   - Understand the difference between:
     * [MEASURED]: Direct physical ESP32 sensor telemetry (active power, voltage, current, DHT22 temperature/humidity).
     * [FORECAST]: ML model predictions (solar generation, household load).
     * [CALCULATED]: Mathematical derivations (safe surplus, conservative load, trapezoidal energy integration).
     * [USER ESTIMATED]: Manually entered solar estimates (stored in Supabase).
   - In accordance with scientific honesty: Branch-level solar generation metering and utility export net-metering are not installed in this prototype; solar generation and savings are modeled/estimated.

4. APPLIANCE SAFETY & SCHEDULING INTERACTION:
   - When the user asks "Can I run [appliance]?" or "When should I run [appliance]?":
     * If required information (appliance name, rated power in kW, run duration in hours/minutes) is missing, ask concise clarifying questions.
     * If sufficient information is provided, call `check_appliance_safety` or `get_schedule_recommendation`.
     * Clearly state the real decision (ALLOW or DENY), available safe surplus buffer, and recommend safer windows if DENIED.

5. CONVERSATION CONTEXT & FOLLOW-UPS:
   - When the user provides follow-up numbers or specifications (e.g. "1500 W for 2 hours" or "tomorrow at 1 PM"), refer to the appliance/topic from preceding messages.

6. USER SOLAR ESTIMATE UPDATES (EXPLICIT CONFIRMATION REQUIRED):
   - If the user states they want to save or update solar generation (e.g. "I generated 3 kWh today" or "Save 3.5 kWh solar estimate"):
     * If the user hasn't explicitly confirmed yet, invoke `update_user_solar_estimate(..., confirmed=False)` or ask for confirmation first.
     * Only perform the actual database write (`confirmed=True`) once the user confirms.

7. PRIVACY & SECURITY:
   - Never reveal API keys, database connection strings, passwords, or internal server configurations.

Keep your answers concise, clear, helpful, and formatted with clean markdown and appropriate units (W, kW, kWh, V, A, °C, %, BDT ৳).
"""

# Bounded conversation context: maximum turns passed to Groq LLM (3 user + 3 assistant turns)
MAX_CONTEXT_TURNS = 6


def get_groq_client() -> Groq:
    """Initialize and return a Groq client instance."""
    if not settings.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not configured in backend environment or .env file.")
    return Groq(api_key=settings.GROQ_API_KEY)


def save_message_to_db(
    session_id: str,
    role: str,
    content: str,
    user_id: Optional[str] = None,
    data_sources: Optional[List[str]] = None,
    tool_calls: Optional[List[str]] = None,
) -> None:
    """Persist a chat message turn to the Supabase chat_messages table (defensive)."""
    try:
        sb = get_supabase()
        record: Dict[str, Any] = {
            "session_id": session_id,
            "role": role,
            "content": content,
            "data_sources": data_sources or [],
            "tool_calls": tool_calls or [],
        }
        if user_id:
            record["user_id"] = user_id

        sb.table("chat_messages").insert(record).execute()
    except Exception as e:
        # Non-blocking: if table does not exist or network glitch, log and continue
        logger.debug(f"Could not persist chat message to Supabase: {e}")


def load_chat_history(
    session_id: str,
    user_id: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Load persistent chronological chat messages for a session and user from Supabase."""
    try:
        sb = get_supabase()
        q = (
            sb.table("chat_messages")
            .select("*")
            .eq("session_id", session_id)
        )
        if user_id:
            q = q.eq("user_id", user_id)
        res = q.order("created_at", desc=False).limit(limit).execute()
        return res.data or []
    except Exception as e:
        logger.debug(f"Could not load chat history from Supabase: {e}")
        return []


def delete_chat_history(session_id: str, user_id: Optional[str] = None) -> bool:
    """Clear all chat messages for a session and user from Supabase."""
    try:
        sb = get_supabase()
        q = sb.table("chat_messages").delete().eq("session_id", session_id)
        if user_id:
            q = q.eq("user_id", user_id)
        q.execute()
        return True
    except Exception as e:
        logger.debug(f"Could not delete chat history from Supabase: {e}")
        return False


async def process_chat_message(
    user_message: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Process a user message through Groq LLM with safe tool-calling loop and session persistence."""
    # Ensure session_id exists
    active_session_id = session_id.strip() if session_id and session_id.strip() else str(uuid.uuid4())

    if not user_message or not user_message.strip():
        return {
            "session_id": active_session_id,
            "answer": "Hello! How can I help you with your solar energy, live telemetry, or appliance scheduling today?",
            "data_sources": [],
            "tool_calls": [],
        }

    # Save user message to persistent DB
    save_message_to_db(active_session_id, "user", user_message, user_id=user_id)

    dhaka_now = get_dhaka_now()
    current_context = (
        f"\n[System Context: Current local time in Kaliakair, Bangladesh is "
        f"{dhaka_now.strftime('%Y-%m-%d %I:%M %p BST')}. "
        f"Today's date is {dhaka_now.strftime('%Y-%m-%d')}.]\n"
    )

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT + current_context}
    ]

    # Resolve past history turns for LLM context:
    # 1. Prefer database history if available
    db_history = load_chat_history(active_session_id, user_id=user_id, limit=20)
    context_turns: List[Dict[str, str]] = []

    if db_history and len(db_history) > 1:
        # Exclude the very last row which is the current user message just inserted
        for row in db_history[:-1]:
            context_turns.append({"role": row["role"], "content": row["content"]})
    elif conversation_history:
        for turn in conversation_history:
            role = turn.get("role")
            content = turn.get("content")
            if role in ("user", "assistant") and content:
                context_turns.append({"role": role, "content": str(content)})

    # Pass a bounded recent context window (last MAX_CONTEXT_TURNS) to prevent token bloat
    if context_turns:
        for turn in context_turns[-MAX_CONTEXT_TURNS:]:
            messages.append({"role": turn["role"], "content": turn["content"]})

    messages.append({"role": "user", "content": user_message})

    try:
        client = get_groq_client()
    except Exception as e:
        logger.error(f"Groq client initialization error: {e}")
        err_reply = "The AI Assistant is currently unable to connect because the Groq API key is not configured. Please check backend settings."
        save_message_to_db(active_session_id, "assistant", err_reply)
        return {
            "session_id": active_session_id,
            "answer": err_reply,
            "data_sources": [],
            "tool_calls": [],
            "error": "api_key_unconfigured",
        }

    max_tool_iterations = 5
    executed_tools: List[str] = []
    collected_provenance: set[str] = set()

    for iteration in range(max_tool_iterations):
        response = None
        for retry in range(3):
            try:
                response = client.chat.completions.create(
                    model=settings.GROQ_MODEL,
                    messages=messages,
                    tools=HEMS_TOOLS_SCHEMA,
                    tool_choice="auto",
                    temperature=0.2,
                    max_tokens=800,
                )
                break
            except Exception as e:
                err_str = str(e).lower()
                if "rate limit" in err_str or "429" in err_str:
                    import asyncio
                    await asyncio.sleep(2.5 * (retry + 1))
                else:
                    logger.error(f"Groq API completion error: {e}")
                    fail_reply = "I encountered an error communicating with the AI service. Please try again in a moment."
                    save_message_to_db(active_session_id, "assistant", fail_reply, user_id=user_id, data_sources=list(collected_provenance), tool_calls=executed_tools)
                    return {
                        "session_id": active_session_id,
                        "answer": fail_reply,
                        "data_sources": list(collected_provenance),
                        "tool_calls": executed_tools,
                        "error": str(e),
                    }
        if response is None:
            rate_reply = "The AI Assistant is currently receiving high traffic. Please try again in a few seconds."
            save_message_to_db(active_session_id, "assistant", rate_reply, user_id=user_id, data_sources=list(collected_provenance), tool_calls=executed_tools)
            return {
                "session_id": active_session_id,
                "answer": rate_reply,
                "data_sources": list(collected_provenance),
                "tool_calls": executed_tools,
                "error": "rate_limit_exceeded",
            }

        choice = response.choices[0]
        msg = choice.message

        # If LLM didn't call any tools, we have our final text answer
        if not msg.tool_calls:
            final_answer = msg.content or "I have processed your request."
            save_message_to_db(active_session_id, "assistant", final_answer, user_id=user_id, data_sources=list(collected_provenance), tool_calls=executed_tools)
            return {
                "session_id": active_session_id,
                "answer": final_answer,
                "data_sources": list(collected_provenance),
                "tool_calls": executed_tools,
            }

        # LLM requested one or more tool calls
        messages.append(msg)

        for tc in msg.tool_calls:
            func_name = tc.function.name
            func_args_str = tc.function.arguments
            executed_tools.append(func_name)

            try:
                args = json.loads(func_args_str) if func_args_str else {}
            except Exception:
                args = {}

            # Execute the tool safely
            try:
                tool_result, prov = await execute_tool_call(func_name, args)
                if prov and prov != "[UNKNOWN]":
                    collected_provenance.add(prov)
            except Exception as ex:
                tool_result = {"status": "error", "message": f"Execution failed: {str(ex)}"}

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "name": func_name,
                "content": json.dumps(tool_result),
            })

    # If reached max tool iterations, return answer and persist
    fallback_answer = "I have retrieved the requested energy data."
    save_message_to_db(active_session_id, "assistant", fallback_answer, user_id=user_id, data_sources=list(collected_provenance), tool_calls=executed_tools)
    return {
        "session_id": active_session_id,
        "answer": fallback_answer,
        "data_sources": list(collected_provenance),
        "tool_calls": executed_tools,
    }
