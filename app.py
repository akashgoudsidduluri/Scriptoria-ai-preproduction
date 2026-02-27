import requests
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, Response
import uuid
import json

app = Flask(__name__)
app.secret_key = "scriptoria-secret-key"


def call_ollama(prompt):
    """Call Ollama and return full response"""
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
        result = response.json()["response"]
        print(f"[OLLAMA] Response length: {len(result)}")
        return result
    except requests.exceptions.ConnectionError as e:
        print(f"[ERROR] Cannot connect to Ollama at {url}")
        raise Exception("Cannot connect to Ollama. Is it running at localhost:11434?")
    except Exception as e:
        print(f"[ERROR] Ollama error: {str(e)}")
        raise


def call_ollama_stream(prompt):
    """Call Ollama with streaming enabled - yields text chunks as they arrive"""
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


@app.route('/health')
def health():
    return jsonify({"status": "ok"}), 200


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/set_username', methods=['POST'])
def set_username():
    data = request.json
    username = data.get("username", "Guest")

    session["username"] = username
    session["session_id"] = str(uuid.uuid4())

    return jsonify({"success": True})


@app.route('/dashboard')
def dashboard():
    if "username" not in session:
        return redirect(url_for('index'))

    return render_template("dashboard.html", username=session["username"])


@app.route('/generate_story', methods=['POST'])
def generate_story():
    try:
        data = request.json
        storyline = data.get("storyline", "")

        if not storyline:
            return jsonify({"error": "Storyline missing"}), 400

        print(f"[GENERATE] Received: {storyline[:50]}...")
        
        prompt = f"Write a short cinematic screenplay with scene heading and dialogue:\n{storyline}"
        print(f"[GENERATE] Calling Ollama (streaming)...")
        
        # Stream the response back to client
        def generate():
            full_text = ""
            for chunk in call_ollama_stream(prompt):
                full_text += chunk
                # Send chunk as JSON event
                yield f"data: {json.dumps({'text': chunk})}\n\n"
            print(f"[GENERATE] Complete response: {len(full_text)} chars")
        
        return Response(generate(), mimetype='text/event-stream')
    except Exception as e:
        print(f"[ERROR] Generate failed: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)