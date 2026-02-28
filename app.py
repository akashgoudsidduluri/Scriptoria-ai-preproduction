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
        char_ids  = data.get("character_ids", [])

        if not storyline:
            return jsonify({"error": "Storyline missing"}), 400

        user_id_fixed = session.get("user_id")
        
        # --- CONTEXT INJECTION (Character Bible) ---
        character_blobs = []
        if user_id_fixed and char_ids:
            from database import _get_client, DB_MODE
            # Fetch full character details for the selected IDs
            if DB_MODE == "local":
                import local_db
                for cid in char_ids:
                    # Simple local fetch
                    res = local_db._run_query("SELECT * FROM characters WHERE id = ?", (cid,), fetch_all=False)
                    if res: character_blobs.append(f"{res['name']}: {res['description']}. (Personality: {res.get('personality') or 'N/A'})")
            else:
                res = _get_client().table("characters").select("*").in_("id", char_ids).execute()
                for char in res.data:
                    character_blobs.append(f"{char['name']}: {char['description']}. (Personality: {char.get('personality') or 'N/A'})")
        
        char_context = "\n".join([f"- {blob}" for blob in character_blobs])
        
        prompt = f"""You are a cinematic screenwriter.
Write a short screenplay based on the story idea below.

{f"CHARACTER BIBLE (Ensure these characters match these descriptions exactly):" if char_context else ""}
{char_context if char_context else ""}

STORY IDEA:
{storyline}

Formatting: Use standard Hollywood screenplay format (Scene headings, character names centered, dialogues).
"""

        print(f"\n[STORY START] user: {user_id_fixed} chars: {len(char_ids)}")

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
                    if item:
                        yield f"data: {json.dumps({'metadata': item})}\n\n"
                except Exception as db_err:
                    print(f"[DB ERROR] Save failed: {db_err}")
            
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
# Character Bible
# ─────────────────────────────────────────────────────────────

@app.route('/generate_character', methods=['POST'])
@login_required
def gen_character():
    """Use AI to generate a character profile based on a name or small prompt."""
    data = request.json or {}
    input_text = data.get("name", "").strip() or "a random unique character"
    
    prompt = f"""You are a master cinematic storyteller and historical researcher.
Generate a detailed character profile for: "{input_text}"

CRITICAL RULES:
1. If "{input_text}" is a historical figure, freedom fighter, or well-known person (e.g., Sitarama Raju, Bheem, Gandhi), you MUST describe them according to their historical reality, era (1920s), and actual legacy. 
2. Do NOT invent modern roles like "software engineer" or "ML researcher" if the context is clearly historical or cinematic.
3. If they are a fictional character archetype, make them cinematic and gritty.

FORMAT YOUR RESPONSE EXACTLY LIKE THIS:
Name: [Character Name]
Description: [2-3 sentences on appearance, role, and era significance]
Personality: [Key traits, core values, and habits]
"""
    
    try:
        full_response = ""
        for chunk in call_ollama_stream(prompt):
            full_response += chunk
        
        # Simple parser for the AI response
        lines = full_response.split("\n")
        char_data = {"name": "", "description": "", "personality": ""}
        for line in lines:
            if line.startswith("Name:"): char_data["name"] = line.replace("Name:", "").strip()
            if line.startswith("Description:"): char_data["description"] = line.replace("Description:", "").strip()
            if line.startswith("Personality:"): char_data["personality"] = line.replace("Personality:", "").strip()
        
        # Fallback if parsing fails
        if not char_data["name"] or not char_data["description"]:
            char_data["name"] = input_text if input_text != "a random unique character" else "Unknown Adventurer"
            char_data["description"] = full_response[:300]
            
        return jsonify(char_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/get_characters', methods=['GET'])
@login_required
def get_chars():
    """Retrieve all character profiles for the user."""
    from database import get_characters
    chars = get_characters(request.current_user_id)
    return jsonify({"characters": chars}), 200


@app.route('/save_character', methods=['POST'])
@login_required
def save_char():
    """Save a character profile."""
    from database import save_character
    data = request.json or {}
    name = data.get("name", "").strip()
    desc = data.get("description", "").strip()
    pers = data.get("personality", "").strip()

    if not name or not desc:
        return jsonify({"error": "Name and description are required"}), 400

    result = save_character(request.current_user_id, name, desc, pers)
    if isinstance(result, dict):
        return jsonify({"success": True, "character": result}), 200
    
    # Return specific DB error message
    return jsonify({"error": result or "Failed to save character"}), 500


@app.route('/delete_character', methods=['POST'])
@login_required
def delete_char():
    """Delete a character profile."""
    from database import delete_character
    data = request.json or {}
    char_id = data.get("id")

    if not char_id:
        return jsonify({"error": "Character ID required"}), 400

    delete_character(char_id, request.current_user_id)
    return jsonify({"success": True}), 200

@app.route('/download_pdf', methods=['POST'])
def download_pdf():
    data = request.json or {}
    screenplay = data.get('screenplay', '')
    char_ids = data.get('character_ids', [])
    if not screenplay: return jsonify({"error": "No content"}), 400

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    
    # --- ADD CHARACTER BIBLE TO PDF ---
    if char_ids:
        from database import _get_client, DB_MODE
        elements.append(Paragraph("CHARACTER BIBLE", styles["Heading1"]))
        elements.append(Spacer(1, 12))
        
        char_blobs = []
        if DB_MODE == "local":
            import local_db
            for cid in char_ids:
                char = local_db._run_query("SELECT * FROM characters WHERE id = ?", (cid,), fetch_one=True)
                if char: char_blobs.append(char)
        else:
            res = _get_client().table("characters").select("*").in_("id", char_ids).execute()
            char_blobs = res.data
            
        for char in char_blobs:
            elements.append(Paragraph(f"<b>{char['name']}</b>", styles["Heading3"]))
            elements.append(Paragraph(char['description'], styles["Normal"]))
            if char.get('personality'):
                elements.append(Paragraph(f"<i>Personality: {char['personality']}</i>", styles["Italic"]))
            elements.append(Spacer(1, 12))
        
        elements.append(Paragraph("<hr/>", styles["Normal"])) # Separator
        elements.append(Spacer(1, 24))

    # Screenplay Content
    elements.append(Paragraph("SCREENPLAY", styles["Heading1"]))
    elements.append(Spacer(1, 12))
    for line in screenplay.split("\n"):
        safe = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        elements.append(Paragraph(safe or "&nbsp;", styles["Normal"]))
        elements.append(Spacer(1, 4))
    
    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='screenplay.pdf', mimetype='application/pdf')


@app.route('/download_docx', methods=['POST'])
def download_docx():
    data = request.json or {}
    screenplay = data.get('screenplay', '')
    char_ids = data.get('character_ids', [])
    if not screenplay: return jsonify({"error": "No content"}), 400

    doc = Document()
    for section in doc.sections:
        section.left_margin, section.right_margin = Inches(1.5), Inches(1)
        section.top_margin, section.bottom_margin = Inches(1), Inches(1)

    # --- ADD CHARACTER BIBLE TO DOCX ---
    if char_ids:
        from database import _get_client, DB_MODE
        doc.add_heading('CHARACTER BIBLE', level=1)
        
        char_blobs = []
        if DB_MODE == "local":
            import local_db
            for cid in char_ids:
                char = local_db._run_query("SELECT * FROM characters WHERE id = ?", (cid,), fetch_one=True)
                if char: char_blobs.append(char)
        else:
            res = _get_client().table("characters").select("*").in_("id", char_ids).execute()
            char_blobs = res.data
            
        for char in char_blobs:
            p = doc.add_paragraph()
            p.add_run(char['name']).bold = True
            doc.add_paragraph(char['description'])
            if char.get('personality'):
                p_p = doc.add_paragraph()
                p_p.add_run(f"Personality: {char['personality']}").italic = True
            doc.add_paragraph() # Spacer
            
        doc.add_page_break()

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