import os
import requests
import base64
from flask import Flask, request

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
API_KEY = os.environ.get("GEMINI_API_KEY", "")

@app.route('/')
def health_check():
    return "Proxy is running!", 200

@app.route('/audio', methods=['POST'])
def audio():
    try:
        raw_data = request.get_data()
        if len(raw_data) < 1000:
            return "Prea putin audio", 400

        print(f"\n[SERVER] Primit {len(raw_data)} bytes.")
        audio_b64_in = base64.b64encode(raw_data).decode('utf-8')

        # Cerem doar transcrierea, fara generare audio (mult mai rapid)
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key=" + API_KEY
        payload = {
            "contents": [{
                "parts": [
                    {"text": "Transcrie exact ce se aude in acest audio. Returneaza doar textul, fara introduceri."},
                    {"inlineData": {"mimeType": "audio/pcm;rate=16000", "data": audio_b64_in}}
                ]
            }]
        }

        print("[SERVER] Trimitere STT catre Google...")
        response = requests.post(url, json=payload, timeout=25)
        
        if response.status_code != 200:
            print(f"[SERVER] Eroare Google: {response.status_code}")
            return f"Eroare Google: {response.status_code}", 200

        resp_json = response.json()
        parts = resp_json.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        
        text_out = "Nu am inteles."
        for part in parts:
            if "text" in part:
                text_out = part["text"]
                break

        print(f"[SERVER] Transcriere: {text_out}")
        return text_out, 200

    except Exception as e:
        print(f"[SERVER] Exceptie: {e}")
        return f"Exceptie: {str(e)}", 200
