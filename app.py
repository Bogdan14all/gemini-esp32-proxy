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
        raw_data = request.get_data()
        if len(raw_data) < 1000:
            return "Prea putin audio", 400

        print(f"\n[SERVER] Primit {len(raw_data)} bytes.")
        audio_b64_in = base64.b64encode(raw_data).decode('utf-8')

        # Folosim modelul sugerat de Google pentru text/audio
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key=" + API_KEY
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": "Asculta acest audio si raspunde scurt in romana."},
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
        
        # Afisam in log-urile Render exact ce a raspuns Google
        print(f"[SERVER] Cod Google: {response.status_code}")
        
        # Încercăm să citim răspunsul
        try:
            resp_json = response.json()
        except Exception:
            print(f"[SERVER] Google a trimis HTML sau text invalid: {response.text[:200]}")
            return "Eroare: Google a trimis un raspuns invalid.", 200

        # Dacă Google a trimis o eroare (ex: model ocupat, fara acces)
        if "error" in resp_json:
            err_msg = resp_json["error"].get("message", "Eroare necunoscuta")
            print(f"[SERVER] Eroare Google: {err_msg}")
            # Returnam 200 ca ESP32-ul sa poata citi mesajul curat
            return f"Google: {err_msg[:100]}", 200

        # Dacă a mers bine, extragem sunetul
        try:
            parts = resp_json["candidates"][0]["content"]["parts"]
            audio_out_b64 = None
            for part in parts:
                if "inlineData" in part:
                    audio_out_b64 = part["inlineData"]["data"]
                    break
            
            if not audio_out_b64:
                print("[SERVER] Google nu a trimis audio.")
                return "Eroare: Google nu a trimis audio.", 200

            audio_out_bytes = base64.b64decode(audio_out_b64)
            print(f"[SERVER] Succes! Trimit {len(audio_out_bytes)} bytes inapoi.")
            return Response(audio_out_bytes, mimetype='application/octet-stream')

        except Exception as e:
            print(f"[SERVER] Eroare parsare: {e}")
            print(f"[SERVER] JSON Raw: {resp_json}")
            return f"Eroare parsare: {e}", 200

    except Exception as e:
        print(f"[SERVER] Exceptie fatala: {str(e)}")
        return f"Exceptie server: {str(e)}", 200
