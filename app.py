import requests
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import uuid

app = Flask(__name__)
app.secret_key = "scriptoria-secret-key"


def call_ollama(prompt):
    url = "http://localhost:11434/api/generate"

    payload = {
        "model": "granite4:micro",
        "prompt": prompt,
        "stream": False
    }

    try:
        print(f"[OLLAMA] Calling Ollama at {url}")
        response = requests.post(url, json=payload, timeout=120)
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
        print(f"[GENERATE] Calling Ollama...")
        screenplay = call_ollama(prompt)
        print(f"[GENERATE] Got response: {len(screenplay)} chars")

        return jsonify({"screenplay": screenplay})
    except Exception as e:
        print(f"[ERROR] Generate failed: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)