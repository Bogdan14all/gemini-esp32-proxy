import os
import requests
import base64
from flask import Flask, request, Response

app = Flask(__name__)
API_KEY = os.environ.get("GEMINI_API_KEY", "")

@app.route('/')
def health_check():
    return "Proxy is running!", 200

@app.route('/audio', methods=['POST'])
def audio():
    try:
        # Preluăm datele audio brute (Raw Bytes) de la ESP32
        raw_data = request.get_data()
        
        if len(raw_data) < 1000:
            print(f"\n[SERVER] Eroare: Am primit doar {len(raw_data)} bytes.")
            return "Prea putin audio", 400

        print(f"\n[SERVER] Primit {len(raw_data)} bytes de sunet de la ESP32.")
        
        # Transformăm în Base64 pentru Google
        audio_b64_in = base64.b64encode(raw_data).decode('utf-8')

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
                "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Puck"}}}
            }
        }

        print("[SERVER] Trimitere catre Google...")
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code != 200:
            print(f"[SERVER] Eroare Google: {response.text}")
            return f"Eroare Google: {response.text}", 500

        resp_json = response.json()
        
        audio_out_b64 = None
        try:
            parts = resp_json["candidates"][0]["content"]["parts"]
            for part in parts:
                if "inlineData" in part:
                    audio_out_b64 = part["inlineData"]["data"]
                    break
        except Exception as e:
            print(f"[SERVER] Eroare parsare: {e}")
            return "Eroare parsare Google", 500

        if not audio_out_b64:
            return "Google nu a trimis audio", 500

        # Decodăm sunetul primit de la Google înapoi în bytes bruți
        audio_out_bytes = base64.b64decode(audio_out_b64)
        print(f"[SERVER] Succes! Trimitere {len(audio_out_bytes)} bytes de sunet inapoi la ESP32.")
        
        # Trimitem sunetul brut direct către ESP32 (fără JSON)
        return Response(audio_out_bytes, mimetype='application/octet-stream')

    except Exception as e:
        print(f"[SERVER] Exceptie: {str(e)}")
        return str(e), 500
