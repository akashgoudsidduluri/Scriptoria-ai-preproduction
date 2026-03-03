# Scriptoria

Scriptoria is a Flask-based web application that uses **Supabase as a managed PostgreSQL database** and **Ollama (granite4:micro)** for local AI screenplay generation.

Supabase Auth is **not used**.  
Authentication and session management are handled entirely in Flask.

---

## 📦 Project Structure

```
app.py
auth.py
database.py
supabase_schema.sql
requirements.txt
.env.example

static/
  ├─ script.js
  └─ style.css

templates/
  ├─ index.html
  └─ dashboard.html
```

---

## 🏗 Architecture

- Flask = backend server
- Supabase = hosted PostgreSQL database
- Ollama = local LLM inference
- `service_role` key = server-side only
- No client-side database access
- No Supabase Auth

The frontend never communicates directly with Supabase.

---

## 🚀 Getting Started

### 1️⃣ Clone repository

```bash
git clone <repo-url>
cd scriptoria
```

---

### 2️⃣ Create virtual environment

**Windows**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux**
```bash
python -m venv venv
source venv/bin/activate
```

---

### 3️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

---

### 4️⃣ Configure environment variables

Copy the example file:

```bash
copy .env.example .env   # Windows
# or
cp .env.example .env     # macOS/Linux
```

Edit `.env`:

```
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key
FLASK_SECRET_KEY=your_long_random_secret
```

Generate a proper Flask secret:

```python
import secrets
print(secrets.token_hex(32))
```

### ⚠️ Critical Security Rules

- Never commit `.env`
- Never expose `SUPABASE_SERVICE_KEY` to frontend
- If service_role key is leaked, regenerate immediately in Supabase dashboard
- Only backend uses Supabase

---

### 5️⃣ Apply database schema

Open Supabase dashboard → SQL Editor  
Paste contents of `supabase_schema.sql`  
Click **Run**

This creates required tables:

- users
- sessions
- chat_history
- characters

---

### 6️⃣ Setup Ollama (local LLM)

Install Ollama:

https://ollama.com

Pull model:

```bash
ollama pull granite4:micro
```

---

### 7️⃣ Run application

```bash
python app.py
```

Open:

```
http://localhost:5000
```

---

## 🔍 Using the App

1. Register or log in
2. Create character profiles (optional)
3. Generate screenplay ideas
4. AI responses stream live via Ollama
5. Export screenplay as PDF or DOCX

---

## 🗄 Database Notes

- Supabase is used only as PostgreSQL.
- Supabase Auth is not used.
- `service_role` key bypasses RLS.
- RLS may remain enabled; it does not affect service_role access.

---

## 🛠 Production Deployment

The built-in Flask server is for development only.

For production:

```bash
gunicorn app:app
```

Set environment variables in your hosting platform (Render, Railway, etc.).  
Do not rely on `.env` in production.

---

## ✅ What to Commit

Commit:

- Source code
- `supabase_schema.sql`
- `requirements.txt`
- `.env.example`
- README.md

Do NOT commit:

- `.env`
- `venv/`
- `__pycache__/`
- `*.pyc`
- Logs

---

## 🔁 Git Workflow

Create branch:

```bash
git checkout -b supabase-only
```

Commit changes:

```bash
git add .
git commit -m "Implement Supabase backend with service_role"
git push -u origin supabase-only
```

Merge to main when ready.

---

## 🔐 Security Model

- Backend fully trusted
- service_role key stored server-side only
- Manual password hashing in Flask
- Session management handled in Flask
- Entire database accessible to backend

If the server is compromised, the database is compromised.

For stricter production security:
- Implement RLS policies
- Use JWT verification
- Consider Supabase Auth

---

## 📌 Summary

Scriptoria uses:

- Flask for backend logic
- Supabase as managed PostgreSQL
- service_role key (server-only)
- Ollama for local AI inference

No direct client database access.  
No Supabase Auth.