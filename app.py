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

        print(f"\n[SERVER] Primit {len(raw_data)} bytes de la ESP32.")
        audio_b64_in = base64.b64encode(raw_data).decode('utf-8')

        # Lista de modele de rezervă (Fallback)
        models_to_try = ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.0-flash"]
        
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

        final_audio_out = None
        error_message = ""

        for model in models_to_try:
            print(f"[SERVER] Incercare model: {model}")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key=" + API_KEY
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = requests.post(url, json=payload, timeout=60)

                    if response.status_code == 503:
                        wait_time = 2 ** attempt
                        print(f"[SERVER] {model} ocupat (503). Reincerc in {wait_time}s...")
                        time.sleep(wait_time)
                        continue # Reincearca acelasi model
                    
                    elif response.status_code == 404:
                        print(f"[SERVER] {model} nu exista (404). Trec la urmatorul model...")
                        break # Iese din bucla de retry si trece la urmatorul model din lista
                    
                    elif response.status_code != 200:
                        print(f"[SERVER] Eroare HTTP {response.status_code} la {model}.")
                        error_message = f"Eroare {response.status_code}"
                        break # Iese si trece la urmatorul model

                    # Daca e 200 OK, procesam
                    resp_json = response.json()
                    parts = resp_json["candidates"][0]["content"]["parts"]
                    for part in parts:
                        if "inlineData" in part:
                            final_audio_out = part["inlineData"]["data"]
                            break
                    
                    if final_audio_out:
                        print(f"[SERVER] Succes cu modelul {model}!")
                        break # Iese din bucla de retry
                        
                except Exception as e:
                    print(f"[SERVER] Eroare retea la {model}: {str(e)}")
                    error_message = str(e)
                    time.sleep(2)

            if final_audio_out:
                break # Daca am gasit audio, oprim căutarea

        if not final_audio_out:
            print(f"[SERVER] Toate modelele au esuat. Ultima eroare: {error_message}")
            return f"Toate modelele au esuat. {error_message}", 500

        # Trimitem inapoi audio-ul brut
        audio_out_bytes = base64.b64decode(final_audio_out)
        print(f"[SERVER] Trimit {len(audio_out_bytes)} bytes inapoi la ESP32.")
        return Response(audio_out_bytes, mimetype='application/octet-stream')

    except Exception as e:
        print(f"[SERVER] Eroare fatala: {str(e)}")
        return str(e), 500
