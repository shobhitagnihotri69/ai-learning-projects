import time
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
except ImportError:
    WebClient = None
    class SlackApiError(Exception):
        response = {"error": "slack_sdk not installed"}
from ..config import config
from ..utils.logger import create_module_logger

logger = create_module_logger("slack-actions")

_web_client: Optional[WebClient] = None
_user_client: Optional[WebClient] = None

def get_slack_clients() -> tuple[WebClient, Optional[WebClient]]:
    global _web_client, _user_client
    if _web_client is None:
        _web_client = WebClient(token=config.slack.bot_token)
    if _user_client is None and config.slack.user_token:
        _user_client = WebClient(token=config.slack.user_token)
    return _web_client, _user_client

# ============================================
# User Operations
# ============================================

def get_user_info(user_id: str) -> Optional[Dict[str, Any]]:
    client, _ = get_slack_clients()
    try:
        res = client.users_info(user=user_id)
        user = res.get("user")
        if not user:
            return None
        return {
            "id": user["id"],
            "name": user.get("name", "unknown"),
            "real_name": user.get("real_name", user.get("name", "unknown")),
            "email": user.get("profile", {}).get("email"),
        }
    except SlackApiError as e:
        logger.error(f"Error fetching user {user_id}: {e.response['error']}")
        return None

def find_user(query: str) -> Optional[Dict[str, Any]]:
    client, _ = get_slack_clients()
    clean_query = query.lstrip("@").lower()
    try:
        res = client.users_list()
        for user in res.get("members", []):
            if user.get("deleted"):
                continue
            name = user.get("name", "").lower()
            real = user.get("real_name", "").lower()
            email = user.get("profile", {}).get("email", "").lower()
            if clean_query in (name, real, email):
                return {
                    "id": user["id"],
                    "name": user.get("name", "unknown"),
                    "real_name": user.get("real_name", user.get("name", "unknown")),
                }
        return None
    except SlackApiError as e:
        logger.error(f"Error finding user {query}: {e.response['error']}")
        return None

def list_users() -> List[Dict[str, Any]]:
    client, _ = get_slack_clients()
    try:
        res = client.users_list()
        users = []
        for u in res.get("members", []):
            if not u.get("deleted") and not u.get("is_bot"):
                users.append({
                    "id": u["id"],
                    "name": u.get("name", ""),
                    "real_name": u.get("real_name", u.get("name", "")),
                    "email": u.get("profile", {}).get("email")
                })
        return users
    except SlackApiError as e:
        logger.error(f"Error listing users: {e.response['error']}")
        return []

# ============================================
# Channel Operations
# ============================================

def find_channel(query: str) -> Optional[Dict[str, Any]]:
    client, _ = get_slack_clients()
    clean_query = query.lstrip("#").lower()
    try:
        res = client.conversations_list(types="public_channel,private_channel", limit=200)
        for ch in res.get("channels", []):
            if ch.get("name", "").lower() == clean_query or ch.get("id", "").lower() == clean_query:
                return {
                    "id": ch["id"],
                    "name": ch.get("name", ""),
                    "is_member": ch.get("is_member", False),
                    "is_private": ch.get("is_private", False)
                }
        return None
    except SlackApiError as e:
        logger.error(f"Error finding channel {query}: {e.response['error']}")
        return None

def list_channels() -> List[Dict[str, Any]]:
    client, _ = get_slack_clients()
    try:
        res = client.conversations_list(types="public_channel,private_channel", limit=100)
        channels = []
        for ch in res.get("channels", []):
            if not ch.get("is_archived"):
                channels.append({
                    "id": ch["id"],
                    "name": ch.get("name", ""),
                    "is_member": ch.get("is_member", False),
                    "is_private": ch.get("is_private", False)
                })
        return channels
    except SlackApiError as e:
        logger.error(f"Error listing channels: {e.response['error']}")
        return []

# ============================================
# Messaging Operations
# ============================================

def send_message(target: str, message: str, thread_ts: Optional[str] = None) -> Dict[str, Any]:
    client, _ = get_slack_clients()
    channel_id = target
    
    # Check if target is a channel name or username
    if target.startswith("#"):
        ch = find_channel(target)
        if not ch:
            return {"success": False, "error": f"Channel {target} not found"}
        channel_id = ch["id"]
    elif target.startswith("@"):
        u = find_user(target)
        if not u:
            return {"success": False, "error": f"User {target} not found"}
        # Open DM
        dm = client.conversations_open(users=u["id"])
        channel_id = dm["channel"]["id"]

    try:
        res = client.chat_postMessage(channel=channel_id, text=message, thread_ts=thread_ts)
        return {"success": True, "ts": res["ts"], "channel": channel_id}
    except SlackApiError as e:
        logger.error(f"Error sending message to {target}: {e.response['error']}")
        return {"success": False, "error": e.response["error"]}

def get_channel_history(channel_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    client, _ = get_slack_clients()
    try:
        res = client.conversations_history(channel=channel_id, limit=limit)
        messages = []
        for m in res.get("messages", []):
            if not m.get("subtype"):
                messages.append({
                    "ts": m.get("ts"),
                    "user": m.get("user"),
                    "text": m.get("text", ""),
                    "thread_ts": m.get("thread_ts")
                })
        return messages
    except SlackApiError as e:
        logger.error(f"Error fetching channel history: {e.response['error']}")
        return []

def search_messages(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    client, user_client = get_slack_clients()
    # Slack search.messages requires user token (xoxp-)
    search_client = user_client or client
    try:
        res = search_client.search_messages(query=query, count=limit)
        matches = res.get("messages", {}).get("matches", [])
        return [
            {
                "text": m.get("text"),
                "channel": m.get("channel", {}).get("name"),
                "username": m.get("username"),
                "ts": m.get("ts"),
                "permalink": m.get("permalink")
            }
            for m in matches
        ]
    except SlackApiError as e:
        logger.warning(f"Slack search API error (may require user token xoxp-): {e.response['error']}")
        return []

# ============================================
# Scheduling & Reminders
# ============================================

def schedule_message(target: str, message: str, send_at_ts: int) -> Dict[str, Any]:
    client, _ = get_slack_clients()
    channel_id = target
    if target.startswith("#"):
        ch = find_channel(target)
        if not ch:
            return {"success": False, "error": f"Channel {target} not found"}
        channel_id = ch["id"]

    try:
        res = client.chat_scheduleMessage(channel=channel_id, text=message, post_at=send_at_ts)
        return {"success": True, "scheduled_message_id": res["scheduled_message_id"]}
    except SlackApiError as e:
        logger.error(f"Error scheduling message: {e.response['error']}")
        return {"success": False, "error": e.response["error"]}

def set_reminder(user_id: str, text: str, time_str: str) -> Dict[str, Any]:
    _, user_client = get_slack_clients()
    if user_client:
        try:
            res = user_client.reminders_add(text=text, time=time_str, user=user_id)
            return {"success": True, "reminder": res.get("reminder")}
        except SlackApiError as e:
            logger.error(f"Error creating Slack reminder: {e.response['error']}")
            return {"success": False, "error": e.response["error"]}
    else:
        # Fallback: schedule a direct message reminder to the user
        client, _ = get_slack_clients()
        try:
            dm = client.conversations_open(users=user_id)
            dm_channel = dm["channel"]["id"]
            # Simple 10-minute fallback or send immediately
            post_at = int(time.time()) + 600
            res = client.chat_scheduleMessage(
                channel=dm_channel,
                text=f"⏰ *Reminder:* {text}",
                post_at=post_at
            )
            return {"success": True, "note": "Scheduled DM fallback reminder"}
        except Exception as e:
            return {"success": False, "error": str(e)}
