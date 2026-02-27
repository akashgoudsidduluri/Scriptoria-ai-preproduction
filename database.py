"""
database.py  –  Supabase client + helper queries for Scriptoria
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load .env file automatically
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

_supabase_client: Client | None = None

def _get_client() -> Client:
    """Return (and lazily create) the Supabase client."""
    global _supabase_client
    if _supabase_client is None:
        url = os.environ.get("SUPABASE_URL", SUPABASE_URL)
        key = os.environ.get("SUPABASE_SERVICE_KEY", SUPABASE_SERVICE_KEY)
        if not url or not key:
            print("[DB ERROR] Supabase credentials missing from .env")
            raise RuntimeError("Supabase credentials missing.")
        
        try:
            _supabase_client = create_client(url, key)
            print("[DB] Supabase client initialized.")
        except Exception as e:
            print(f"[DB ERROR] Failed to create client: {e}")
            raise e
            
    return _supabase_client


# ─────────────────────────────────────────────────────────────
# USER QUERIES
# ─────────────────────────────────────────────────────────────

def create_user(username: str, email: str, password_hash: str):
    """Insert a new user. Returns the created user row or raises on duplicate."""
    try:
        result = _get_client().table("users").insert({
            "username": username, 
            "email": email, 
            "password_hash": password_hash
        }).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"[DB ERROR] create_user failed: {e}")
        raise e


def get_user_by_email(email: str):
    """Fetch a user row by email. Uses limit(1) to avoid PGRST116 errors."""
    try:
        result = _get_client().table("users").select("*").eq("email", email).limit(1).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"[DB ERROR] get_user_by_email failed: {e}")
        raise e


def get_user_by_username(username: str):
    """Fetch a user row by username. Uses limit(1) to avoid PGRST116 errors."""
    try:
        result = _get_client().table("users").select("*").eq("username", username).limit(1).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"[DB ERROR] get_user_by_username failed: {e}")
        raise e


def get_user_by_id(user_id: str):
    """Fetch a user row by UUID."""
    try:
        result = _get_client().table("users").select("id, username, email, created_at").eq("id", user_id).limit(1).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"[DB ERROR] get_user_by_id failed: {e}")
        raise e


# ─────────────────────────────────────────────────────────────
# SESSION QUERIES
# ─────────────────────────────────────────────────────────────

def create_session(user_id: str, session_token: str):
    """Store a new login session token."""
    try:
        result = _get_client().table("sessions").insert({
            "user_id": user_id, 
            "session_token": session_token
        }).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"[DB ERROR] create_session failed: {e}")
        raise e


def get_session(session_token: str):
    """Retrieve a session by token. Uses limit(1) to avoid PGRST116 errors."""
    try:
        result = (
            _get_client().table("sessions")
            .select("*, users(id, username, email)")
            .eq("session_token", session_token)
            .gt("expires_at", "now()")
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"[DB ERROR] get_session failed: {e}")
        raise e


def delete_session(session_token: str):
    """Delete a session (logout)."""
    try:
        _get_client().table("sessions").delete().eq("session_token", session_token).execute()
    except Exception as e:
        print(f"[DB ERROR] delete_session failed: {e}")


# ─────────────────────────────────────────────────────────────
# CHAT HISTORY QUERIES
# ─────────────────────────────────────────────────────────────

def save_chat(user_id: str, prompt: str, response: str, title: str = None):
    """Save a prompt + AI response + title to chat_history."""
    try:
        result = _get_client().table("chat_history").insert({
            "user_id": user_id, 
            "prompt": prompt, 
            "response": response,
            "title": title
        }).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"[DB ERROR] save_chat failed: {e}")
        return None


def get_chat_history(user_id: str, limit: int = 20):
    """Fetch the N most recent chat entries for a user, newest first."""
    try:
        result = (
            _get_client().table("chat_history")
            .select("id, prompt, response, title, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data
    except Exception as e:
        print(f"[DB ERROR] get_chat_history failed: {e}")
        return []


def update_chat_title(chat_id: str, user_id: str, new_title: str):
    """Update the title of a specific chat entry."""
    try:
        result = _get_client().table("chat_history").update({
            "title": new_title
        }).eq("id", chat_id).eq("user_id", user_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"[DB ERROR] update_chat_title failed: {e}")
        return None


def delete_chat_entry(chat_id: str, user_id: str):
    """Delete a single chat entry (only if it belongs to the user)."""
    try:
        _get_client().table("chat_history").delete().eq("id", chat_id).eq("user_id", user_id).execute()
    except Exception as e:
        print(f"[DB ERROR] delete_chat_entry failed: {e}")


def clear_chat_history(user_id: str):
    """Delete all chat history for a user."""
    try:
        _get_client().table("chat_history").delete().eq("user_id", user_id).execute()
    except Exception as e:
        print(f"[DB ERROR] clear_chat_history failed: {e}")
