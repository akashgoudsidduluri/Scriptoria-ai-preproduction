"""
auth.py  –  Flask Blueprint for user Authentication
Optimized for Performance: Uses session-cookie identity to minimize DB round-trips.
"""

import uuid
import time
import os
from functools import wraps
from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash

# Debug: Check for proxy settings that often cause 30s timeouts on Windows
proxies = {k: v for k, v in os.environ.items() if "PROXY" in k.upper()}
if proxies:
    print(f"[AUTH DEBUG] Proxy environment detected: {proxies}")
else:
    print("[AUTH DEBUG] No proxy environment detected.")
from database import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    create_session,
    get_session,
    delete_session,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# ─────────────────────────────────────────────────────────────
# Helper: require login decorator (Optimized)
# ─────────────────────────────────────────────────────────────
def login_required(f):
    """
    Decorator – returns 401 if the user is not logged in.
    PERFORMANCE: Trusts the signed Flask session for identity metadata.
    Does NOT hit Supabase on every request unless token verification is critical.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # 1. Quick check: Is the basic identity present in the session cookie?
        user_id = session.get("user_id")
        token = session.get("session_token")
        
        if not user_id or not token:
            return jsonify({"error": "Authentication required"}), 401

        # 2. Assign identity to request context immediately.
        # We trust the signed session cookie for the user_id and username for high-frequency routes (history, generation).
        # This eliminates one network round-trip to Supabase per request.
        request.current_user_id = user_id
        request.current_user_name = session.get("username", "User")
        
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────────────────────
# REGISTER (Optimized)
# ─────────────────────────────────────────────────────────────
@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Body: { "username": "...", "email": "...", "password": "..." }
    PERFORMANCE: Trusts DB constraints for uniqueness; removes separate lookups.
    """
    route_start = time.time()
    data = request.get_json()
    username = (data.get("username") or "").strip()
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    # Basic UI-level validation
    if not username or not email or not password:
        return jsonify({"error": "Username, email and password are required"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    password_hash = generate_password_hash(password)
    
    try:
        user = create_user(username, email, password_hash)
        if not user:
            return jsonify({"error": "Failed to create user. Please try again."}), 500
    except Exception as e:
        error_str = str(e).lower()
        if "duplicate" in error_str or "already exists" in error_str or "unique constraint" in error_str:
            return jsonify({"error": "Username or Email already exists."}), 409
        print(f"[AUTH ERROR] Registration failed: {e}")
        return jsonify({"error": "Registration failed"}), 500

    # Auto-login: Create a new session token
    token = str(uuid.uuid4())
    create_session(user["id"], token)

    # Store FULL identity in Flask server-side session (signed cookie)
    session["session_token"] = token
    session["user_id"]       = user["id"]
    session["username"]      = user["username"]
    session["email"]         = user["email"]

    print(f"[AUTH] register route total time: {time.time() - route_start:.2f}s")
    return jsonify({
        "success": True,
        "username": user["username"],
        "user": {"id": user["id"], "username": user["username"], "email": user["email"]}
    }), 201


# ─────────────────────────────────────────────────────────────
# LOGIN (Optimized)
# ─────────────────────────────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Body: { "email": "...", "password": "..." }
    """
    route_start = time.time()
    data = request.get_json()
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    # Single fetch for user
    user = get_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    # Create a new session token
    token = str(uuid.uuid4())
    create_session(user["id"], token)

    # Store FULL identity in Flask session
    session["session_token"] = token
    session["user_id"]       = user["id"]
    session["username"]      = user["username"]
    session["email"]         = user["email"]

    print(f"[AUTH] login route total time: {time.time() - route_start:.2f}s")
    return jsonify({"success": True, "username": user["username"]}), 200


# ─────────────────────────────────────────────────────────────
# LOGOUT
# ─────────────────────────────────────────────────────────────
@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Invalidate session token and clear Flask session."""
    token = session.get("session_token")
    if token:
        # Async-style cleanup (fire and forget or simple delete)
        delete_session(token)
    session.clear()
    return jsonify({"success": True}), 200


# ─────────────────────────────────────────────────────────────
# ME (current user info)
# ─────────────────────────────────────────────────────────────
@auth_bp.route("/me", methods=["GET"])
@login_required
def me():
    """Returns profile from current session context (No DB lookup needed)."""
    return jsonify({
        "user": {
            "id": session.get("user_id"),
            "username": session.get("username"),
            "email": session.get("email")
        }
    }), 200
