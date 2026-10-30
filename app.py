import os
import requests
import base64
from flask import Flask, request, Response

app = Flask(__name__)
# Îi spunem lui Flask să accepte fișiere audio mari (până la 16MB)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 

API_KEY = os.environ.get("GEMINI_API_KEY", "")

@app.route('/')
def health_check():
    return "Proxy is running!", 200

@app.route('/audio', methods=['POST'])
def audio():
    try:
        raw_data = request.get_data()
        print(f"\n[SERVER] Primit {len(raw_data)} bytes.")
        
        if len(raw_data) < 1000:
            return "Prea putin audio", 400

        audio_b64_in = base64.b64encode(raw_data).decode('utf-8')

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

        print("[SERVER] Trimitere catre Google (timeout 25s)...")
        # Setam timeout la 25 de secunde ca sa nu ne omoare Render-ul la 30s
        response = requests.post(url, json=payload, timeout=25)
        
        print(f"[SERVER] Cod Google: {response.status_code}")
        
        try:
            resp_json = response.json()
        except Exception:
            print(f"[SERVER] Google a trimis HTML: {response.text[:100]}")
            return "Eroare: Google a trimis HTML.", 200

        if "error" in resp_json:
            err_msg = resp_json["error"].get("message", "Eroare necunoscuta")
            print(f"[SERVER] Eroare Google: {err_msg}")
            return f"Google: {err_msg[:80]}", 200

        try:
            parts = resp_json["candidates"][0]["content"]["parts"]
            audio_out_b64 = None
            for part in parts:
                if "inlineData" in part:
                    audio_out_b64 = part["inlineData"]["data"]
                    break
            
            if not audio_out_b64:
                return "Eroare: Fara audio in raspuns.", 200

            audio_out_bytes = base64.b64decode(audio_out_b64)
            print(f"[SERVER] Succes! Trimit {len(audio_out_bytes)} bytes inapoi.")
            return Response(audio_out_bytes, mimetype='application/octet-stream')

        except Exception as e:
            print(f"[SERVER] Eroare parsare: {e}")
            return f"Eroare parsare: {e}", 200

    except requests.exceptions.Timeout:
        print("[SERVER] Eroare: Google a depasit timpul de 25 secunde!")
        return "Eroare: Google a raspuns prea greu.", 200
    except Exception as e:
        print(f"[SERVER] Exceptie fatala: {str(e)}")
        return f"Exceptie server: {str(e)}", 200
