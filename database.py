"""
database.py  –  Supabase client + helper queries for Scriptoria
Includes emergency performance patches and local fallback.
"""

import os
import time
from dotenv import load_dotenv
from supabase import create_client, Client

# Load .env file automatically
load_dotenv()

# --- EMERGENCY PERFORMANCE PATCH: FIX 40s TIMEOUT ---
# Forced IPv4 + Proxy Bypass: Stops Windows from stalling on DNS/Proxy discovery.
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
if SUPABASE_URL:
    from urllib.parse import urlparse
    domain = urlparse(SUPABASE_URL).netloc
    os.environ["NO_PROXY"] = f"{domain},localhost,127.0.0.1"

SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
DB_MODE = os.environ.get("DB_MODE", "supabase").lower()

_supabase_client: Client | None = None

def _get_client() -> Client:
    """Return (and lazily create) the Supabase client."""
    global _supabase_client
    if _supabase_client is None:
        url = os.environ.get("SUPABASE_URL", SUPABASE_URL)
        key = os.environ.get("SUPABASE_SERVICE_KEY", SUPABASE_SERVICE_KEY)
        if not url or not key: raise RuntimeError("Supabase credentials missing.")
        
        try:
            import time
            from supabase.lib.client_options import ClientOptions
            start = time.time()
            
            # PERFORMANCE FIX: Set a reasonable timeout for Postgrest.
            # (Removed storage_client_timeout as it caused attribute errors in some versions)
            client_options = ClientOptions(
                postgrest_client_timeout=15,
            )
            
            _supabase_client = create_client(url, key, options=client_options)
            print(f"[DB] Supabase (Cloud) initialized in {time.time() - start:.4f}s")
        except Exception as e:
            print(f"[DB ERROR] Client failed: {e}")
            raise e
    return _supabase_client

# ─────────────────────────────────────────────────────────────
# ROUTED QUERIES (Supabase vs Local)
# ─────────────────────────────────────────────────────────────

def create_user(username: str, email: str, password_hash: str):
    if DB_MODE == "local":
        import local_db
        return local_db.create_user(username, email, password_hash)
    
    try:
        start = time.time()
        result = _get_client().table("users").insert({
            "username": username, "email": email, "password_hash": password_hash
        }).execute()
        print(f"[DB] create_user took {time.time() - start:.2f}s")
        return result.data[0] if result.data else None
    except Exception as e:
        raise e

def get_user_by_email(email: str):
    if DB_MODE == "local":
        import local_db
        return local_db.get_user_by_email(email)
    
    try:
        start = time.time()
        result = _get_client().table("users").select("*").eq("email", email).limit(1).execute()
        print(f"[DB] get_user_by_email took {time.time() - start:.2f}s")
        return result.data[0] if result.data else None
    except Exception as e:
        raise e

def get_user_by_id(user_id: str):
    if DB_MODE == "local":
        import local_db
        return local_db.get_user_by_id(user_id)
    
    try:
        result = _get_client().table("users").select("*").eq("id", user_id).limit(1).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        raise e

def create_session(user_id: str, session_token: str):
    if DB_MODE == "local":
        import local_db
        return local_db.create_session(user_id, session_token)
    
    try:
        start = time.time()
        result = _get_client().table("sessions").insert({
            "user_id": user_id, "session_token": session_token
        }).execute()
        print(f"[DB] create_session took {time.time() - start:.2f}s")
        return result.data[0] if result.data else None
    except Exception as e:
        raise e

def get_session(session_token: str):
    if DB_MODE == "local":
        import local_db
        return local_db.get_session(session_token)
    
    try:
        start = time.time()
        result = _get_client().table("sessions").select("*, users(*)").eq("session_token", session_token).gt("expires_at", "now()").limit(1).execute()
        print(f"[DB] get_session took {time.time() - start:.2f}s")
        return result.data[0] if result.data else None
    except Exception as e:
        raise e

def delete_session(session_token: str):
    if DB_MODE == "local":
        import local_db
        return local_db.delete_session(session_token)
    
    _get_client().table("sessions").delete().eq("session_token", session_token).execute()

def save_chat(user_id: str, prompt: str, response: str, title: str = None):
    if DB_MODE == "local":
        import local_db
        return local_db.save_chat(user_id, prompt, response, title)
    
    try:
        start = time.time()
        result = _get_client().table("chat_history").insert({
            "user_id": user_id, "prompt": prompt, "response": response, "title": title
        }).execute()
        print(f"[DB] save_chat took {time.time() - start:.2f}s")
        return result.data[0] if result.data else None
    except Exception as e:
        return None

def get_chat_history(user_id: str, limit: int = 20):
    if DB_MODE == "local":
        import local_db
        return local_db.get_chat_history(user_id, limit)
    
    try:
        start = time.time()
        result = _get_client().table("chat_history").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()
        print(f"[DB] get_chat_history took {time.time() - start:.2f}s")
        return result.data
    except Exception as e:
        return []

def update_chat_title(chat_id: str, user_id: str, new_title: str):
    if DB_MODE == "local":
        # Simplified for mock
        return {"id": chat_id, "title": new_title}
    
    result = _get_client().table("chat_history").update({"title": new_title}).eq("id", chat_id).eq("user_id", user_id).execute()
    return result.data[0] if result.data else None
