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

    response = requests.post(url, json=payload)
    return response.json()["response"]


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
    data = request.json
    storyline = data.get("storyline", "")

    if not storyline:
        return jsonify({"error": "Storyline missing"}), 400


    # ---------- SCREENPLAY ----------
    screenplay_prompt = f"""
You are a cinematic screenplay writer.

Write a short screenplay with scene heading, action and dialogue.

Story:
{storyline}
"""
    screenplay = call_ollama(screenplay_prompt)


    # ---------- CHARACTERS ----------
    character_prompt = f"""
Based on this story, create detailed character profiles with
background, personality and motivation.

Story:
{storyline}
"""
    characters = call_ollama(character_prompt)


    # ---------- SOUND DESIGN ----------
    sound_prompt = f"""
Suggest cinematic background music and sound design for each major scene.

Story:
{storyline}
"""
    sound = call_ollama(sound_prompt)


    session["screenplay"] = screenplay
    session["characters"] = characters
    session["sound"] = sound

    return jsonify({
        "screenplay": screenplay,
        "characters": characters,
        "sound": sound
    })


if __name__ == "__main__":
    app.run(debug=True)