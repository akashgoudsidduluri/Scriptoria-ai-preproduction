import sqlite3
import os
import uuid
from datetime import datetime

DB_PATH = "scriptoria_local.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE,
        email TEXT UNIQUE,
        password_hash TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Sessions table
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        session_token TEXT UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    
    # Chat history table
    c.execute('''CREATE TABLE IF NOT EXISTS chat_history (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        prompt TEXT,
        response TEXT,
        title TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    
    conn.commit()
    conn.close()

# Helper to run queries
def _run_query(query, params=(), fetch_one=False, fetch_all=False, commit=True):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(query, params)
    
    result = None
    if fetch_one:
        row = c.fetchone()
        result = dict(row) if row else None
    elif fetch_all:
        rows = c.fetchall()
        result = [dict(r) for r in rows]
    
    if commit:
        conn.commit()
    conn.close()
    return result

# --- REPLICATING database.py INTERFACE ---

def create_user(username, email, password_hash):
    user_id = str(uuid.uuid4())
    _run_query("INSERT INTO users (id, username, email, password_hash) VALUES (?, ?, ?, ?)",
               (user_id, username, email, password_hash))
    return get_user_by_id(user_id)

def get_user_by_email(email):
    return _run_query("SELECT * FROM users WHERE email = ?", (email,), fetch_one=True)

def get_user_by_id(user_id):
    return _run_query("SELECT id, username, email, created_at FROM users WHERE id = ?", (user_id,), fetch_one=True)

def create_session(user_id, session_token):
    session_id = str(uuid.uuid4())
    expires_at = datetime.now() # Mocked
    _run_query("INSERT INTO sessions (id, user_id, session_token, expires_at) VALUES (?, ?, ?, ?)",
               (session_id, user_id, session_token, expires_at))
    return {"user_id": user_id, "session_token": session_token}

def get_session(session_token):
    # Simplified mock join
    session = _run_query("SELECT * FROM sessions WHERE session_token = ?", (session_token,), fetch_one=True)
    if session:
        user = get_user_by_id(session["user_id"])
        session["users"] = user
    return session

def save_chat(user_id, prompt, response, title):
    chat_id = str(uuid.uuid4())
    _run_query("INSERT INTO chat_history (id, user_id, prompt, response, title) VALUES (?, ?, ?, ?, ?)",
               (chat_id, user_id, prompt, response, title))
    return {"id": chat_id, "user_id": user_id, "prompt": prompt, "response": response, "title": title}

def get_chat_history(user_id, limit=20):
    return _run_query("SELECT * FROM chat_history WHERE user_id = ? ORDER BY created_at DESC LIMIT ?", 
                     (user_id, limit), fetch_all=True)

def delete_session(token):
    _run_query("DELETE FROM sessions WHERE session_token = ?", (token,))

# Auto-init on first import
if not os.path.exists(DB_PATH):
    init_db()
