# Scriptoria

Scriptoria is a Flask-based web application that integrates with Supabase for backend services. It includes authentication, Supabase-backed persistence, and front-end templates for a simple dashboard.

## 📦 Project Structure

```
app.py
auth.py
database.py
static/
  ├─ script.js
  └─ style.css
templates/
  ├─ dashboard.html
  └─ index.html
supabase_schema.sql
requirements.txt
```

## 🚀 Getting Started

1. **Clone the repository**

```bash
git clone <repo-url>
cd scriptoria
```

2. **Create a virtual environment**

```bash
python -m venv venv
source venv/Scripts/activate      # Windows
# or:
# source venv/bin/activate        # macOS/Linux
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Environment configuration**

- Copy `.env.example` to `.env` and fill in your own values.
- Make sure `FLASK_SECRET_KEY` is set to a secure random string.

```bash
cp .env.example .env
# edit .env accordingly
```

5. **Setup ollama (AI model)**

This project uses Ollama with the `granite4:micro` model for local inference. Install Ollama from https://ollama.com and then pull the model:

```bash
ollama pull granite4:micro
```

6. **Run the application**

```bash
python app.py
```

> The server listens on port 5000 by default. Open your browser and go to:
>
> ```text
> http://localhost:5000
> ```
>
> You should see the landing page where you can log in or sign up.

### 🔍 Using the web interface

1. **Authenticate** – register a new user or log in with existing credentials. Session data is stored in Supabase.
2. **Create characters** (optional) from the dashboard; they will be associated with your account.
3. **Generate a screenplay**
   - Click **"New Story"** (or similar button).
   - Enter a story idea, select characters, choose location/BGM tone, and hit **Generate**.
   - The screenplay text will appear streaming in real time (powered by Ollama).
4. **Export options** – once generated you can download the screenplay as PDF or DOCX via the provided buttons.

If you need to view logs or troubleshoot, check the console where `python app.py` is running; database operations and AI prompts are logged there.

## 🛠 Development Tips

- Database: All data lives in Supabase; ensure your project URL/key are configured and the schema (from `supabase_schema.sql`) has been applied.
- Static files are under `static/`; HTML templates reside in `templates/`.

## ⚙️ Detailed setup & deployment

Follow these steps to get a reproducible development environment and to deploy or share the project with others.

1. Create and activate a virtual environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

2. Install Python dependencies

```bash
pip install -r requirements.txt
```

3. Configure environment variables (DO NOT commit `.env`)

- Copy the example file and fill in your Supabase values and `FLASK_SECRET_KEY`:

```bash
copy .env.example .env   # Windows
cp .env.example .env     # macOS / Linux
# Edit .env to add your SUPABASE_URL and SUPABASE_SERVICE_KEY
```

Notes:
- Never commit secrets. `.gitignore` excludes `.env` by default.
- Use the Supabase **service_role** (server-side) key only for server processes — never leak it to the browser or client-side code.

4. Pull the Ollama model (if using local LLM inference)

```bash
ollama pull granite4:micro
```

5. Apply the database schema in Supabase

Options:
- Use the Supabase Dashboard → SQL Editor: open `supabase_schema.sql` and run the statements.
- Or use a DB client/psql with your Supabase DB connection string to run the `supabase_schema.sql` file.

Why keep `supabase_schema.sql` in the repo?
- Yes — keep and commit this file. It documents the table definitions and is essential for reproducible setup, CI, and for teammates or deploy scripts.

6. Start the app

```bash
python app.py
```

Open `http://localhost:5000` and follow the UI flow described earlier.

## ✅ What to commit (recommended)

- Project source code: `app.py`, `auth.py`, `database.py`, `static/`, `templates/`, `requirements.txt`
- SQL schema: `supabase_schema.sql` (yes — commit this)

Optional: use a `migrations/` folder

- If you plan to evolve the schema, consider converting `supabase_schema.sql` into a set of incremental migration files under a `migrations/` directory and commit those instead (or alongside) the single SQL dump.
- Using migrations makes upgrades and rollbacks safer and easier in CI or production deployments. You can use the Supabase Migrations workflow or any migration tool you prefer.

Quick options to apply the schema:

- Supabase Dashboard: open `supabase_schema.sql` in the SQL editor and run it.
- Supabase CLI / migrations: follow Supabase docs to apply migration files from `migrations/`.

Why commit the schema/migrations?
- It documents the DB shape, lets teammates and CI set up databases reproducibly, and provides a source of truth for reviews.
- Documentation: `README.md`, `.env.example`

Do NOT commit:

- Secrets and environment files: `.env`
- Virtual environment: `venv/`
- Python bytecode and caches: `__pycache__/`, `*.pyc`
- Local-only artifacts and logs: `*.log`, OS files like `.DS_Store`

## 🔁 Typical git workflow

```bash
# create a branch
git checkout -b supabase-only

# stage changes
git add .

# commit (use a meaningful message)
git commit -m "Switch to Supabase-only backend; update docs"

# push branch to remote
git push -u origin supabase-only

# open a PR on GitHub/GitLab for review before merging to main
```

If you are ready to update `main` directly and you have permissions:

```bash
git checkout main
git merge supabase-only
git push origin main
```

## 📄 Additional Notes

- `.gitignore` includes Python artifacts, environment files, IDE settings, and logs to keep the repository clean.
- For Supabase setup, refer to the Supabase documentation and ensure service keys are never exposed publicly.

---

Feel free to contribute or report issues! 😊