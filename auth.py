"""
auth.py  –  Flask Blueprint for user Authentication
Endpoints:
  POST /auth/register   – create account
  POST /auth/login      – login, returns session token
  POST /auth/logout     – invalidate session
  GET  /auth/me         – get current logged-in user info
"""

import uuid
from functools import wraps
from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import (
    create_user,
    get_user_by_email,
    get_user_by_username,
    get_user_by_id,
    create_session,
    get_session,
    delete_session,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# ─────────────────────────────────────────────────────────────
# Helper: require login decorator
# ─────────────────────────────────────────────────────────────
def login_required(f):
    """Decorator – returns 401 if the user is not logged in."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = session.get("session_token")
        if not token:
            return jsonify({"error": "Authentication required"}), 401

        db_session = get_session(token)
        if not db_session:
            session.clear()
            return jsonify({"error": "Session expired or invalid"}), 401

        # Attach user info to the request context
        request.current_user = db_session["users"]
        request.current_user_id = db_session["user_id"]
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────────────────────
# REGISTER
# ─────────────────────────────────────────────────────────────
@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Body: { "username": "...", "email": "...", "password": "..." }
    Returns: { "success": true, "user": {...} }
    """
    data = request.get_json()
    username = (data.get("username") or "").strip()
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    # Basic validation
    if not username or not email or not password:
        return jsonify({"error": "username, email and password are required"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    # Check duplicates
    if get_user_by_email(email):
        return jsonify({"error": "Email already in use"}), 409

    if get_user_by_username(username):
        return jsonify({"error": "Username already taken"}), 409

    # Hash password & create user
    password_hash = generate_password_hash(password)
    
    try:
        user = create_user(username, email, password_hash)
        if not user:
            return jsonify({"error": "Failed to create user. Please try again."}), 500
    except Exception as e:
        print(f"[AUTH ERROR] Registration failed: {e}")
        # Usually a duplicate key error if reached here (despite pre-check)
        return jsonify({"error": "Username or Email already exists."}), 409

    # Auto-login: Create a new session token
    token = str(uuid.uuid4())
    create_session(user["id"], token)

    # Store token in Flask server-side session
    session["session_token"] = token
    session["user_id"]       = user["id"]
    session["username"]      = user["username"]

    return jsonify({
        "success": True,
        "username": user["username"],
        "user": {"id": user["id"], "username": user["username"], "email": user["email"]}
    }), 201


# ─────────────────────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Body: { "email": "...", "password": "..." }
    Returns: { "success": true, "username": "..." }
    """
    data = request.get_json()
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = get_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    # Create a new session token
    token = str(uuid.uuid4())
    create_session(user["id"], token)

    # Store token in Flask server-side session
    session["session_token"] = token
    session["user_id"]       = user["id"]
    session["username"]      = user["username"]

    return jsonify({"success": True, "username": user["username"]}), 200


# ─────────────────────────────────────────────────────────────
# LOGOUT
# ─────────────────────────────────────────────────────────────
@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Invalidate session token and clear Flask session."""
    token = session.get("session_token")
    if token:
        delete_session(token)
    session.clear()
    return jsonify({"success": True}), 200


# ─────────────────────────────────────────────────────────────
# ME (current user info)
# ─────────────────────────────────────────────────────────────
@auth_bp.route("/me", methods=["GET"])
@login_required
def me():
    """Returns the currently logged-in user's profile."""
    user = get_user_by_id(request.current_user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"user": user}), 200
