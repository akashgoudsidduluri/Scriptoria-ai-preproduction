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

# Register Auth blueprint
app.register_blueprint(auth_bp)


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def generate_title(prompt_text):
    """Deterministic title generation from prompt (first few words)."""
    words = prompt_text.split()
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

import time

def call_ollama_stream(prompt):
    """Call Ollama with streaming enabled – yields text chunks as they arrive."""
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "granite4:micro",
        "prompt": prompt,
        "stream": True
    }
    try:
        start_time = time.time()
        print(f"[OLLAMA] Request sent at {time.strftime('%H:%M:%S')}")
        response = requests.post(url, json=payload, timeout=180, stream=True)
        
        first_chunk = True
        for line in response.iter_lines():
            if line:
                if first_chunk:
                    print(f"[OLLAMA] First chunk received in {time.time() - start_time:.2f}s")
                    first_chunk = False
                try:
                    chunk = json.loads(line)
                    if "response" in chunk:
                        yield chunk["response"]
                except json.JSONDecodeError:
                    pass
        print(f"[OLLAMA] Total stream duration: {time.time() - start_time:.2f}s")
    except requests.exceptions.ConnectionError:
        yield "ERROR: Cannot connect to Ollama. Is it running at localhost:11434?"
    except Exception as e:
        yield f"ERROR: {str(e)}"


# ─────────────────────────────────────────────────────────────
# Core Routes
# ─────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/dashboard')
def dashboard():
    if "username" not in session:
        return redirect(url_for('index'))
    return render_template("dashboard.html", username=session["username"])


# ─────────────────────────────────────────────────────────────
# Story Generation  (Optimized Streaming)
# ─────────────────────────────────────────────────────────────

@app.route('/generate_story', methods=['POST'])
def generate_story():
    total_start = time.time()
    try:
        data = request.get_json(silent=True) or {}
        storyline = data.get("storyline", "").strip()

        if not storyline:
            return jsonify({"error": "Storyline missing"}), 400

        user_id_fixed = session.get("user_id")

        prompt = f"""Write a short cinematic screenplay with:
- Scene heading
- Character names
- Dialogues
- Proper formatting

Story idea:
{storyline}"""

        print(f"\n[STORY START] user: {user_id_fixed}")

        def generate():
            full_text = ""
            for chunk in call_ollama_stream(prompt):
                full_text += chunk
                yield f"data: {json.dumps({'text': chunk})}\n\n"

            # After generation, save to database and send metadata
            if user_id_fixed and full_text and not full_text.startswith("ERROR:"):
                db_start = time.time()
                try:
                    title = generate_title(storyline)
                    item = save_chat(user_id_fixed, storyline, full_text, title=title)
                    print(f"[DB] Save + Title Title: {time.time() - db_start:.2f}s")
                    
                    if item:
                        yield f"data: {json.dumps({'metadata': item})}\n\n"
                except Exception as db_err:
                    print(f"[DB ERROR] Save failed in {time.time() - db_start:.2f}s: {db_err}")
            
            print(f"[STORY COMPLETE] Total Time: {time.time() - total_start:.2f}s\n")

        return Response(generate(), mimetype='text/event-stream')

    except Exception as e:
        print(f"[ERROR] Generate failed: {str(e)}")
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────
# History
# ─────────────────────────────────────────────────────────────

@app.route('/history', methods=['GET'])
@login_required
def history():
    """Return past generations (Optimized retrieval)."""
    user_id = request.current_user_id
    limit   = int(request.args.get("limit", 20))
    # Note: get_chat_history already uses limit(N) from previous fix
    entries = get_chat_history(user_id, limit=limit)
    return jsonify({"history": entries}), 200


@app.route('/rename_chat', methods=['POST'])
@login_required
def rename_chat():
    """Rename a specific item."""
    from database import update_chat_title
    data = request.json or {}
    chat_id = data.get("id")
    new_title = (data.get("title") or "").strip()

    if not chat_id or not new_title:
        return jsonify({"error": "Chat ID and title are required"}), 400

    result = update_chat_title(chat_id, request.current_user_id, new_title)
    if result:
        return jsonify({"success": True, "title": result["title"]}), 200
    return jsonify({"error": "Failed to rename"}), 500


# ─────────────────────────────────────────────────────────────
# Downloads
# ─────────────────────────────────────────────────────────────

@app.route('/download_pdf', methods=['POST'])
def download_pdf():
    data = request.json or {}
    screenplay = data.get('screenplay', '')
    if not screenplay: return jsonify({"error": "No content"}), 400

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    for line in screenplay.split("\n"):
        safe = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        elements.append(Paragraph(safe or "&nbsp;", styles["Normal"]))
        elements.append(Spacer(1, 6))
    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='screenplay.pdf', mimetype='application/pdf')


@app.route('/download_docx', methods=['POST'])
def download_docx():
    data = request.json or {}
    screenplay = data.get('screenplay', '')
    if not screenplay: return jsonify({"error": "No content"}), 400

    doc = Document()
    for section in doc.sections:
        section.left_margin, section.right_margin = Inches(1.5), Inches(1)
        section.top_margin, section.bottom_margin = Inches(1), Inches(1)

    doc.add_heading('SCREENPLAY', level=0).alignment = WD_ALIGN_PARAGRAPH.CENTER
    for line in screenplay.split("\n"):
        stripped = line.strip()
        para = doc.add_paragraph()
        if stripped.startswith(('INT.', 'EXT.', 'INT ', 'EXT ')) or (stripped.isupper() and 0 < len(stripped) < 60):
            para.add_run(stripped).bold = True
        else:
            para.add_run(stripped)
            
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='screenplay.docx', mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')


if __name__ == "__main__":
    app.run(debug=True)