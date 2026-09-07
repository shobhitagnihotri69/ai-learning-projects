import json
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from openai import OpenAI
from ..config import config
from ..utils.logger import create_module_logger
from ..memory.database import get_session_history, add_message, get_user_tasks
from ..rag import should_use_rag, parse_query_filters, retrieve, build_context_string
from ..memory_ai import search_memory, add_memory, build_memory_context, is_memory_enabled, delete_all_memories
from ..mcp import get_all_mcp_tools, execute_mcp_tool, is_mcp_enabled
from ..tools.slack_actions import (
    send_message,
    get_channel_history,
    search_messages,
    find_user,
    find_channel,
    list_users,
    list_channels,
    schedule_message,
    set_reminder
)
from ..tools.scheduler import task_scheduler
from .prompts import SYSTEM_PROMPT

logger = create_module_logger("agent")

@dataclass
class AgentContext:
    user_id: str
    channel_id: str
    session_id: str
    thread_ts: Optional[str] = None
    user_name: Optional[str] = None

# Built-in Slack Tools (OpenAI function definitions)
BUILTIN_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "send_slack_message",
            "description": "Send a message to a Slack channel or user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Channel name (#general), user (@alice), or channel ID"},
                    "message": {"type": "string", "description": "The message text to send"}
                },
                "required": ["target", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_channel_history",
            "description": "Fetch recent messages from a channel to understand context.",
            "parameters": {
                "type": "object",
                "properties": {
                    "channel": {"type": "string", "description": "Channel name (#general) or channel ID"},
                    "limit": {"type": "integer", "description": "Number of messages to retrieve (default 20)"}
                },
                "required": ["channel"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Search past Slack messages and indexed company knowledge using semantic RAG search.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query to look for in past conversations"},
                    "channel_name": {"type": "string", "description": "Optional channel name to restrict search to"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_channels",
            "description": "List public and private channels the bot is in.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_users",
            "description": "List workspace team members and their handles.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_message",
            "description": "Schedule a message to be posted at a future timestamp.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Channel or user"},
                    "message": {"type": "string", "description": "Message content"},
                    "send_at_seconds_from_now": {"type": "integer", "description": "Delay in seconds from now"}
                },
                "required": ["target", "message", "send_at_seconds_from_now"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_recurring_message",
            "description": "Schedule a recurring message using a cron expression (e.g., daily standup reminder).",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Channel to post to"},
                    "message": {"type": "string", "description": "Message to send"},
                    "cron_expression": {"type": "string", "description": "Standard 5-part cron expression (e.g. '0 10 * * 1-5')"}
                },
                "required": ["target", "message", "cron_expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_reminder",
            "description": "Set a reminder for the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "What to be reminded about"},
                    "time": {"type": "string", "description": "When (e.g., 'in 2 hours', 'tomorrow at 10am')"}
                },
                "required": ["text", "time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "clear_my_memory",
            "description": "Delete all stored memory and preferences for the calling user.",
            "parameters": {"type": "object", "properties": {}}
        }
    }
]

def get_all_tools() -> List[Dict[str, Any]]:
    """Combine built-in Slack tools with dynamic MCP tools."""
    tools = list(BUILTIN_TOOLS)
    if is_mcp_enabled():
        mcp_tools = get_all_mcp_tools()
        tools.extend(mcp_tools)
    return tools

def execute_builtin_tool(name: str, args: Dict[str, Any], context: AgentContext) -> str:
    """Execute a native Slack tool."""
    try:
        if name == "send_slack_message":
            res = send_message(args["target"], args["message"])
            return f"✅ Message sent: {res}" if res.get("success") else f"❌ Failed: {res.get('error')}"

        elif name == "get_channel_history":
            target = args["channel"]
            channel_id = target
            if target.startswith("#"):
                ch = find_channel(target)
                if not ch:
                    return f"Channel {target} not found"
                channel_id = ch["id"]
            messages = get_channel_history(channel_id, limit=args.get("limit", 20))
            if not messages:
                return "No recent messages found."
            formatted = [f"@{m.get('user', 'unknown')}: {m.get('text', '')}" for m in messages]
            return "\n".join(formatted)

        elif name == "search_knowledge_base":
            results = retrieve(args["query"], channel_name=args.get("channel_name"))
            if not results:
                return "No matching documents found in knowledge base."
            return build_context_string(results)

        elif name == "list_channels":
            channels = list_channels()
            member_chans = [f"• #{c['name']}" for c in channels if c.get("is_member")]
            return f"*Channels I'm in ({len(member_chans)}):*\n" + "\n".join(member_chans)

        elif name == "list_users":
            users = list_users()
            items = [f"• {u['real_name']} (@{u['name']})" for u in users[:25]]
            return f"*Users ({len(users)}):*\n" + "\n".join(items)

        elif name == "schedule_message":
            import time
            post_at = int(time.time()) + int(args["send_at_seconds_from_now"])
            res = schedule_message(args["target"], args["message"], post_at)
            return f"✅ Message scheduled: {res}" if res.get("success") else f"❌ Failed: {res.get('error')}"

        elif name == "schedule_recurring_message":
            task_id = task_scheduler.schedule_task(
                user_id=context.user_id,
                channel_id=args["target"],
                task_description=args["message"],
                cron_expression=args["cron_expression"]
            )
            return f"✅ Recurring task scheduled (Task #{task_id}) with cron `{args['cron_expression']}`"

        elif name == "set_reminder":
            res = set_reminder(context.user_id, args["text"], args["time"])
            return f"✅ Reminder set: {res}" if res.get("success") else f"❌ Failed: {res.get('error')}"

        elif name == "clear_my_memory":
            delete_all_memories(context.user_id)
            return "✅ All remembered personal facts and preferences have been deleted."

        return f"Unknown tool: {name}"

    except Exception as e:
        logger.error(f"Error executing builtin tool '{name}': {e}")
        return f"❌ Error executing tool: {str(e)}"

def process_message(user_message: str, context: AgentContext) -> str:
    """Core Agent Loop with RAG, Memory, and Tool Calling."""
    client = OpenAI(api_key=config.ai.openai_api_key)
    
    # 1. Retrieve personalized long-term memory
    memory_context = None
    if is_memory_enabled():
        try:
            memories = search_memory(user_message, user_id=context.user_id)
            memory_context = build_memory_context(memories)
        except Exception as e:
            logger.warning(f"Failed to fetch memory: {e}")

    # 2. Retrieve RAG Slack history context
    rag_context = None
    if should_use_rag(user_message):
        try:
            filters = parse_query_filters(user_message)
            results = retrieve(user_message, channel_name=filters.get("channel_name"))
            if results:
                rag_context = build_context_string(results)
        except Exception as e:
            logger.warning(f"Failed to retrieve RAG context: {e}")

    # 3. Assemble prompt messages
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    if memory_context:
        messages.append({"role": "system", "content": memory_context})

    if rag_context:
        messages.append({
            "role": "system",
            "content": f"Relevant Slack workspace history for context:\n\n{rag_context}"
        })

    # Add conversation history from SQLite
    history = get_session_history(context.session_id, limit=10)
    for msg in history:
        messages.append({
            "role": "user" if msg.role == "user" else "assistant",
            "content": msg.content
        })

    # Add current user query
    messages.append({"role": "user", "content": user_message})

    # Save user message to database
    add_message(
        session_id=context.session_id,
        role="user",
        content=user_message,
        thread_ts=context.thread_ts
    )

    tools = get_all_tools()

    # 4. Native Tool Calling Loop
    max_steps = 8
    step = 0

    while step < max_steps:
        step += 1
        
        response = client.chat.completions.create(
            model=config.ai.default_model,
            messages=messages,
            tools=tools if tools else None,
            tool_choice="auto" if tools else None
        )

        choice = response.choices[0]
        assistant_msg = choice.message
        messages.append(assistant_msg)

        # If no tool calls, this is the final response
        if not assistant_msg.tool_calls:
            final_text = assistant_msg.content or ""
            
            # Save assistant reply to database
            add_message(
                session_id=context.session_id,
                role="assistant",
                content=final_text,
                thread_ts=context.thread_ts
            )

            # Trigger background memory extraction
            if is_memory_enabled():
                def extract_mem():
                    try:
                        add_memory([
                            {"role": "user", "content": user_message},
                            {"role": "assistant", "content": final_text}
                        ], user_id=context.user_id)
                    except Exception as err:
                        logger.debug(f"Background memory extraction note: {err}")
                
                t = threading.Thread(target=extract_mem, daemon=True)
                t.start()

            return final_text

        # Handle tool calls
        for tool_call in assistant_msg.tool_calls:
            fn_name = tool_call.function.name
            try:
                fn_args = json.loads(tool_call.function.arguments)
            except Exception:
                fn_args = {}

            logger.info(f"Executing tool: {fn_name} with args: {fn_args}")

            # Route to MCP or Builtin
            if fn_name.startswith("mcp__"):
                tool_output = execute_mcp_tool(fn_name, fn_args)
            else:
                tool_output = execute_builtin_tool(fn_name, fn_args, context)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(tool_output)
            })

    return "I completed the actions, but reached the maximum tool reasoning steps."

def summarize_thread(messages_text: List[str]) -> str:
    """Summarize a Slack thread."""
    client = OpenAI(api_key=config.ai.openai_api_key)
    joined = "\n".join(messages_text)
    prompt = f"Summarize this Slack conversation concisely in 3-4 bullet points, highlighting decisions and action items:\n\n{joined}"
    
    res = client.chat.completions.create(
        model=config.ai.default_model,
        messages=[
            {"role": "system", "content": "You are a concise executive summary assistant for Slack threads."},
            {"role": "user", "content": prompt}
        ]
    )
    return res.choices[0].message.content or "Could not generate summary."
