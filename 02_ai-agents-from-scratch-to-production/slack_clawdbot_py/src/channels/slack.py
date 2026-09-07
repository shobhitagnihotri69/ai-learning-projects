import re
import threading
from typing import Optional
try:
    from slack_bolt import App
    from slack_bolt.adapter.socket_mode import SocketModeHandler
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
except ImportError:
    class MockApp:
        def event(self, name):
            def decorator(f):
                return f
            return decorator
    App = MockApp
    SocketModeHandler = None
    WebClient = None
    class SlackApiError(Exception):
        pass

from ..config import config
from ..utils.logger import create_module_logger
from ..memory.database import (
    get_or_create_session,
    is_user_approved,
    generate_pairing_code,
    approve_pairing,
    get_thread_messages
)
from ..agents.agent import process_message, summarize_thread, AgentContext

logger = create_module_logger("slack-channel")

# Initialize Bolt App
if App is not None and config.slack.bot_token:
    slack_app = App(
        token=config.slack.bot_token,
        signing_secret=config.slack.signing_secret
    )
    web_client = WebClient(token=config.slack.bot_token) if WebClient else None
else:
    slack_app = MockApp() if 'MockApp' in locals() else None
    web_client = None

socket_handler: Optional[SocketModeHandler] = None
bot_user_id: Optional[str] = None

def get_bot_user_id() -> str:
    global bot_user_id
    if bot_user_id:
        return bot_user_id
    try:
        auth_res = web_client.auth_test()
        bot_user_id = auth_res["user_id"]
        return bot_user_id
    except Exception as e:
        logger.error(f"Failed to get bot user ID: {e}")
        return ""

def add_reaction(channel_id: str, timestamp: str, emoji: str) -> None:
    if not config.features.reactions:
        return
    try:
        web_client.reactions_add(channel=channel_id, timestamp=timestamp, name=emoji)
    except Exception:
        pass

def remove_reaction(channel_id: str, timestamp: str, emoji: str) -> None:
    try:
        web_client.reactions_remove(channel=channel_id, timestamp=timestamp, name=emoji)
    except Exception:
        pass

# ============================================
# Event Listeners
# ============================================

@slack_app.event("app_mention")
def handle_app_mention(event, say, client):
    """Handle @bot mentions in channels."""
    channel_id = event.get("channel")
    user_id = event.get("user")
    ts = event.get("ts")
    thread_ts = event.get("thread_ts") or ts
    raw_text = event.get("text", "")

    bot_id = get_bot_user_id()
    clean_text = re.sub(f"<@{bot_id}>\\s*", "", raw_text).strip()

    logger.info(f"Mention from @{user_id} in #{channel_id}: '{clean_text}'")

    if not clean_text:
        say(text="Hey there! How can I help you today?", thread_ts=thread_ts)
        return

    # Acknowledge with emoji
    add_reaction(channel_id, ts, "eyes")

    try:
        # Check thread summarize request
        if "summarize" in clean_text.lower() and event.get("thread_ts"):
            thread_msgs = get_thread_messages(channel_id, thread_ts)
            if thread_msgs:
                summary = summarize_thread([f"{m.role}: {m.content}" for m in thread_msgs])
                say(text=f"*Thread Summary:*\n{summary}", thread_ts=thread_ts)
                remove_reaction(channel_id, ts, "eyes")
                add_reaction(channel_id, ts, "white_check_mark")
                return

        session = get_or_create_session(
            user_id=user_id,
            channel_id=channel_id,
            thread_ts=thread_ts,
            session_type="channel"
        )

        context = AgentContext(
            user_id=user_id,
            channel_id=channel_id,
            session_id=session.id,
            thread_ts=thread_ts
        )

        reply = process_message(clean_text, context)
        say(text=reply, thread_ts=thread_ts)
        remove_reaction(channel_id, ts, "eyes")
        add_reaction(channel_id, ts, "white_check_mark")

    except Exception as e:
        logger.error(f"Error handling mention: {e}")
        say(text=f"⚠️ An error occurred while processing your request: {str(e)}", thread_ts=thread_ts)
        remove_reaction(channel_id, ts, "eyes")
        add_reaction(channel_id, ts, "x")

@slack_app.event("message")
def handle_direct_message(event, say, client):
    """Handle 1-on-1 Direct Messages."""
    channel_type = event.get("channel_type")
    # Only process direct messages (im)
    if channel_type != "im":
        return

    # Ignore bot's own messages or edits
    if event.get("subtype") or event.get("bot_id"):
        return

    user_id = event.get("user")
    channel_id = event.get("channel")
    text = event.get("text", "").strip()
    ts = event.get("ts")

    logger.info(f"Direct Message from @{user_id}: '{text}'")

    # Handle DM approval pairing security
    if config.features.require_approval and not is_user_approved(user_id):
        # Check if user submitted pairing code
        code_match = re.match(r"^[A-F0-9]{6}$", text.upper())
        if code_match:
            code = code_match.group(0)
            if approve_pairing(code, approved_by=user_id):
                say("✅ Pairing code approved! You now have full access to ClawdBot.")
                return
            else:
                say("❌ Invalid or expired pairing code.")
                return

        # Otherwise provide pairing code instructions
        new_code = generate_pairing_code(user_id)
        say(f"🔒 *Access Restricted*\nPlease ask an admin to approve your access code: `{new_code}`")
        return

    add_reaction(channel_id, ts, "thinking_face")

    try:
        session = get_or_create_session(
            user_id=user_id,
            channel_id=channel_id,
            session_type="dm"
        )

        context = AgentContext(
            user_id=user_id,
            channel_id=channel_id,
            session_id=session.id
        )

        reply = process_message(text, context)
        say(text=reply)
        remove_reaction(channel_id, ts, "thinking_face")
    except Exception as e:
        logger.error(f"Error handling DM: {e}")
        say(text=f"⚠️ Something went wrong: {str(e)}")
        remove_reaction(channel_id, ts, "thinking_face")

def start_slack_app() -> None:
    """Start Slack App with Socket Mode Handler."""
    global socket_handler
    if not config.slack.app_token or not config.slack.bot_token:
        logger.error("Missing SLACK_APP_TOKEN or SLACK_BOT_TOKEN in environment")
        return

    logger.info("Connecting to Slack via Socket Mode...")
    socket_handler = SocketModeHandler(slack_app, config.slack.app_token)
    
    # Run socket connection in a separate thread so it doesn't block startup
    t = threading.Thread(target=socket_handler.start, daemon=True)
    t.start()
    logger.info("✅ Slack Socket Mode connected")

def stop_slack_app() -> None:
    """Close Slack Socket Mode connection."""
    global socket_handler
    if socket_handler is not None:
        try:
            socket_handler.close()
            logger.info("Slack Socket Mode disconnected")
        except Exception as e:
            logger.error(f"Error stopping Slack Socket Mode: {e}")
        finally:
            socket_handler = None
