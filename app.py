import requests
import uuid
import json
from io import BytesIO

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, Response, send_file
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

from auth import auth_bp, login_required
from database import save_chat, get_chat_history

app = Flask(__name__)
app.secret_key = "scriptoria-secret-key"

@app.errorhandler(Exception)
def handle_exception(e):
    """Log any unhandled exception."""
    print(f"[SERVER ERROR] {str(e)}")
    import traceback
    traceback.print_exc()
    return jsonify({"error": str(e)}), 500

# Register Auth blueprint  (/auth/register, /auth/login, /auth/logout, /auth/me)
app.register_blueprint(auth_bp)


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def generate_title(prompt_text):
    """Deterministic title generation from prompt (first few words)."""
    words = prompt_text.split()
    # Filter out short/filler words if desired, but keep it simple
    meaningful = [w for w in words if len(w) > 2][:6]
    title = " ".join(meaningful)
    if len(title) > 40:
        title = title[:37] + "..."
    if not title:
        title = "Untitled Story"
    return title.capitalize()


# ─────────────────────────────────────────────────────────────
# Ollama helpers
# ─────────────────────────────────────────────────────────────

def call_ollama(prompt):
    """Call Ollama and return full response (non-streaming)."""
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "granite4:micro",
        "prompt": prompt,
        "stream": False
    }
    try:
        print(f"[OLLAMA] Calling Ollama at {url}")
        response = requests.post(url, json=payload, timeout=180)
        print(f"[OLLAMA] Status: {response.status_code}")
        result = response.json().get("response", "")
        print(f"[OLLAMA] Response length: {len(result)}")
        return result
    except requests.exceptions.ConnectionError:
        raise Exception("Cannot connect to Ollama. Is it running at localhost:11434?")
    except Exception as e:
        raise Exception(str(e))


def call_ollama_stream(prompt):
    """Call Ollama with streaming enabled – yields text chunks as they arrive."""
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "granite4:micro",
        "prompt": prompt,
        "stream": True
    }
    try:
        print(f"[OLLAMA-STREAM] Calling Ollama at {url}")
        response = requests.post(url, json=payload, timeout=180, stream=True)
        print(f"[OLLAMA-STREAM] Status: {response.status_code}")
        for line in response.iter_lines():
            if line:
                try:
                    chunk = json.loads(line)
                    if "response" in chunk:
                        yield chunk["response"]
                except json.JSONDecodeError:
                    pass
    except requests.exceptions.ConnectionError:
        yield "ERROR: Cannot connect to Ollama. Is it running at localhost:11434?"
    except Exception as e:
        yield f"ERROR: {str(e)}"


# ─────────────────────────────────────────────────────────────
# Core Routes
# ─────────────────────────────────────────────────────────────

@app.route('/health')
def health():
    return jsonify({"status": "ok"}), 200


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/set_username', methods=['POST'])
def set_username():
    data = request.json or {}
    username = data.get("username", "Guest")
    session["username"] = username
    session["session_id"] = str(uuid.uuid4())
    return jsonify({"success": True})


@app.route('/dashboard')
def dashboard():
    if "username" not in session:
        return redirect(url_for('index'))
    return render_template("dashboard.html", username=session["username"])


# ─────────────────────────────────────────────────────────────
# Story Generation  (streaming, saves to Supabase when logged in)
# ─────────────────────────────────────────────────────────────

@app.route('/generate_story', methods=['POST'])
def generate_story():
    try:
        data = request.get_json(silent=True) or {}
        storyline = data.get("storyline", "").strip()

        if not storyline:
            return jsonify({"error": "Storyline missing"}), 400

        print(f"[GENERATE] Received: {storyline[:50]}...")

        # Improved prompt format
        prompt = f"""Write a short cinematic screenplay with:
- Scene heading
- Character names
- Dialogues
- Proper formatting

Story idea:
{storyline}"""

        print("[GENERATE] Calling Ollama (streaming)...")

        # Capture user_id upfront! Streaming generators can lose session context 
        # if accessed after the main request thread finishes yielding.
        user_id_fixed = session.get("user_id")

        def generate():
            full_text = ""
            for chunk in call_ollama_stream(prompt):
                full_text += chunk
                yield f"data: {json.dumps({'text': chunk})}\n\n"

            print(f"[GENERATE] Complete response: {len(full_text)} chars")

            # Save to Supabase (with title) using the fixed ID
            if user_id_fixed and full_text and not full_text.startswith("ERROR:"):
                try:
                    title = generate_title(storyline)
                    print(f"[DB] Saving story for user {user_id_fixed}: '{title}'")
                    result = save_chat(user_id_fixed, storyline, full_text, title=title)
                    if result:
                        print(f"[DB SUCCESS] History saved with ID: {result.get('id')}")
                    else:
                        print("[DB WARNING] save_chat returned None. Check database.py logs.")
                except Exception as db_err:
                    print(f"[DB ERROR] Save failed: {db_err}")
            else:
                if not user_id_fixed:
                    print("[DB SKIP] User not logged in, skipping save.")

        return Response(generate(), mimetype='text/event-stream')

    except Exception as e:
        print(f"[ERROR] Generate failed: {str(e)}")
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────
# Download Routes
# ─────────────────────────────────────────────────────────────

@app.route('/download_pdf', methods=['POST'])
def download_pdf():
    """Generate and return a real PDF using ReportLab."""
    data = request.json or {}
    screenplay = data.get('screenplay', '')

    if not screenplay:
        return jsonify({"error": "No screenplay provided"}), 400

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    for line in screenplay.split("\n"):
        safe_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        elements.append(Paragraph(safe_line or "&nbsp;", styles["Normal"]))
        elements.append(Spacer(1, 6))

    doc.build(elements)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name='screenplay.pdf',
        mimetype='application/pdf'
    )


@app.route('/download_docx', methods=['POST'])
def download_docx():
    """Generate and return a real DOCX using python-docx."""
    data = request.json or {}
    screenplay = data.get('screenplay', '')

    if not screenplay:
        return jsonify({"error": "No screenplay provided"}), 400

    doc = Document()

    # Page margins: standard screenplay format
    for section in doc.sections:
        section.left_margin  = Inches(1.5)
        section.right_margin = Inches(1)
        section.top_margin   = Inches(1)
        section.bottom_margin = Inches(1)

    # Title
    title = doc.add_heading('SCREENPLAY', level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    for line in screenplay.split("\n"):
        stripped = line.strip()
        para = doc.add_paragraph()

        # Scene headings: bold
        if stripped.startswith(('INT.', 'EXT.', 'INT ', 'EXT ')) or (
            stripped.isupper() and 0 < len(stripped) < 60
        ):
            run = para.add_run(stripped)
            run.bold = True
            run.font.size = Pt(11)
        else:
            run = para.add_run(stripped)
            run.font.size = Pt(11)

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name='screenplay.docx',
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )


# ─────────────────────────────────────────────────────────────
# Chat History
# ─────────────────────────────────────────────────────────────

@app.route('/history', methods=['GET'])
@login_required
def history():
    """Return the logged-in user's past story generations."""
    user_id = request.current_user_id
    limit   = int(request.args.get("limit", 20))
    entries = get_chat_history(user_id, limit=limit)
    return jsonify({"history": entries}), 200


@app.route('/rename_chat', methods=['POST'])
@login_required
def rename_chat():
    """Rename a specific chat history item."""
    from database import update_chat_title
    data = request.json or {}
    chat_id = data.get("id")
    new_title = (data.get("title") or "").strip()

    if not chat_id or not new_title:
        return jsonify({"error": "Chat ID and new title are required"}), 400

    result = update_chat_title(chat_id, request.current_user_id, new_title)
    if result:
        return jsonify({"success": True, "title": result["title"]}), 200
    else:
        return jsonify({"error": "Failed to rename story. Please try again."}), 500


if __name__ == "__main__":
    app.run(debug=True)