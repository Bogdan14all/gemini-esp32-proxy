import os
import requests
import base64
import time
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

        max_retries = 3
        response = None
        
        for attempt in range(max_retries):
            try:
                print(f"[SERVER] Incercarea {attempt + 1}/{max_retries}...")
                response = requests.post(url, json=payload, timeout=60)

                if response.status_code == 503:
                    wait_time = 2 ** attempt
                    print(f"[SERVER] Eroare 503. Reincerc in {wait_time} secunde...")
                    time.sleep(wait_time)
                    continue
                elif response.status_code != 200:
                    print(f"[SERVER] Eroare HTTP {response.status_code}: {response.text}")
                    return f"Eroare Google: {response.status_code}", 500

                break  # Dacă e 200 OK, ieșim din buclă
                
            except requests.exceptions.RequestException as e:
                print(f"[SERVER] Exceptie retea: {str(e)}")
                if attempt == max_retries - 1:
                    return f"Eroare retea: {str(e)}", 500
                time.sleep(2 ** attempt)
        else:
            return "Serverul Google este supraaglomerat. Incearca din nou.", 503

        if response is None:
            return "Nu s-a primit raspuns de la Google", 500

        resp_json = response.json()
        audio_out_b64 = None
        try:
            parts = resp_json["candidates"][0]["content"]["parts"]
            for part in parts:
                if "inlineData" in part:
                    audio_out_b64 = part["inlineData"]["data"]
                    break
        except Exception as e:
            print(f"[SERVER] Eroare parsare raspuns: {e}")
            return "Eroare parsare raspuns Google", 500

        if not audio_out_b64:
            return "Google nu a trimis audio", 500

        audio_out_bytes = base64.b64decode(audio_out_b64)
        print(f"[SERVER] Succes! Trimit {len(audio_out_bytes)} bytes inapoi.")
        return Response(audio_out_bytes, mimetype='application/octet-stream')

    except Exception as e:
        print(f"[SERVER] Exceptie generala: {str(e)}")
        return str(e), 500
