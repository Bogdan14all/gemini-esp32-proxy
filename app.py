import os
import requests
import base64
from flask import Flask, request, jsonify

app = Flask(__name__)

API_KEY = os.environ.get("GEMINI_API_KEY", "")

@app.route('/')
def health_check():
    return "Proxy is running!", 200

# Ruta pentru TEXT (o pastram pentru test)
@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    prompt = data.get('text', 'Salut!')
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=" + API_KEY
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=20)
        resp_json = response.json()
        text = resp_json["candidates"][0]["content"]["parts"][0]["text"]
        return jsonify({"status": "ok", "text": text})
    except Exception as e:
        return jsonify({"status": "error", "text": str(e)}), 200

# Ruta pentru AUDIO (Noua functionalitate)
@app.route('/audio', methods=['POST'])
def audio():
    try:
        data = request.json
        audio_b64_in = data.get('audio')
        if not audio_b64_in:
            return jsonify({"status": "error", "text": "Nu am primit audio."}), 200

        print(f"\n[SERVER] Audio primit de la ESP32 (Base64 len: {len(audio_b64_in)})")

        # Construim cererea pentru Gemini (Audio Input -> Audio Output)
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=" + API_KEY
        payload = {
            "contents": [{
                "parts": [
                    {"text": "Asculta acest audio si raspunde scurt si natural in romana."},
                    {"inlineData": {"mimeType": "audio/pcm;rate=16000", "data": audio_b64_in}}
                ]
            }],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Puck"}}
                }
            }
        }

        print("[SERVER] Trimitere catre Google...")
        response = requests.post(url, json=payload, timeout=60)
        
        resp_json = response.json()
        
        # Extragem sunetul din răspunsul Google
        audio_out_b64 = None
        try:
            parts = resp_json["candidates"][0]["content"]["parts"]
            for part in parts:
                if "inlineData" in part:
                    audio_out_b64 = part["inlineData"]["data"]
                    break
        except Exception as e:
            print(f"[SERVER] Eroare parsare raspuns: {e}")
            print(resp_json)
            return jsonify({"status": "error", "text": "Google nu a trimis audio."}), 200

        if audio_out_b64:
            print(f"[SERVER] Succes! Trimitere audio inapoi la ESP32 (len: {len(audio_out_b64)})")
            return jsonify({"status": "ok", "audio": audio_out_b64})
        else:
            return jsonify({"status": "error", "text": "Fara audio in raspuns."}), 200

    except Exception as e:
        print(f"[SERVER] Exceptie: {str(e)}")
        return jsonify({"status": "error", "text": str(e)}), 200
