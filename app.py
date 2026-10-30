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

        # Folosim modelul recomandat, cu suport audio
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

        # Implementăm reîncercarea cu backoff exponențial
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"[SERVER] Încercarea {attempt + 1}/{max_retries}...")
                response = requests.post(url, json=payload, timeout=60)

                if response.status_code == 503:
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    print(f"[SERVER] Eroare 503. Reîncerc în {wait_time} secunde...")
                    time.sleep(wait_time)
                    continue # Trecem la următoarea încercare
                elif response.status_code != 200:
                    print(f"[SERVER] Eroare HTTP {response.status_code}: {response.text}")
                    return f"Eroare Google: {response.status_code}", 500

                # Dacă am primit 200 OK, ieșim din buclă
                break
        else:
            # Dacă am epuizat toate încercările
            return "Serverul Google este supraaglomerat. Încearcă din nou.", 503

        resp_json = response.json()
        audio_out_b64 = None
        try:
            parts = resp_json["candidates"][0]["content"]["parts"]
            for part in parts:
                if "inlineData" in part:
                    audio_out_b64 = part["inlineData"]["data"]
                    break
        except Exception as e:
            print(f"[SERVER] Eroare parsare răspuns: {e}")
            return "Eroare parsare răspuns Google", 500

        if not audio_out_b64:
            return "Google nu a trimis audio", 500

        audio_out_bytes = base64.b64decode(audio_out_b64)
        print(f"[SERVER] Succes! Trimit {len(audio_out_bytes)} bytes înapoi.")
        return Response(audio_out_bytes, mimetype='application/octet-stream')

    except Exception as e:
        print(f"[SERVER] Excepție: {str(e)}")
        return str(e), 500
