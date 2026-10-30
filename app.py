import os
import requests
import base64
import time
from flask import Flask, request, Response

app = Flask(__name__)
# Permitem request-uri mari (audio)
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

        # Modele de rezervă, în caz că unul este indisponibil sau ocupat
        models_to_try = ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-1.5-flash"]
        
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

        final_audio_out = None
        last_error = ""

        for model in models_to_try:
            print(f"[SERVER] Incercare model: {model}")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
            
            # Încercăm de 2 ori pentru fiecare model (în caz de eroare 503 temporară)
            for attempt in range(2):
                try:
                    # Timeout strict la 20 secunde pentru a nu depăși limita Render (30s)
                    response = requests.post(url, json=payload, timeout=20)
                    
                    if response.status_code == 200:
                        resp_json = response.json()
                        parts = resp_json.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                        for part in parts:
                            if "inlineData" in part:
                                final_audio_out = part["inlineData"]["data"]
                                break
                        
                        if final_audio_out:
                            print(f"[SERVER] Succes cu {model}!")
                            break # Ieșim din bucla de 'attempt'
                    
                    elif response.status_code == 503:
                        print(f"[SERVER] {model} ocupat (503). Incerc din nou in 2s...")
                        time.sleep(2)
                    
                    elif response.status_code == 404:
                        print(f"[SERVER] {model} nu exista (404). Trec la urmatorul...")
                        break # Trecem la urmatorul model din listă
                    
                    else:
                        last_error = f"Cod {response.status_code}"
                        print(f"[SERVER] Eroare {last_error}: {response.text[:100]}")
                        break # Trecem la următorul model

                except requests.exceptions.Timeout:
                    print(f"[SERVER] {model} a expirat (Timeout). Trec la urmatorul...")
                    last_error = "Timeout"
                    break # Trecem la următorul model
                except Exception as e:
                    print(f"[SERVER] Eroare {model}: {str(e)}")
                    last_error = str(e)
                    break
            
            if final_audio_out:
                break # Dacă avem audio, nu mai încercăm alte modele

        if not final_audio_out:
            print(f"[SERVER] Esec total. Ultima eroare: {last_error}")
            return f"Eroare server: {last_error}", 200

        # Decodăm audio-ul din Base64 și îl trimitem ca bytes
        audio_out_bytes = base64.b64decode(final_audio_out)
        print(f"[SERVER] Trimit {len(audio_out_bytes)} bytes audio inapoi la ESP32.")
        return Response(audio_out_bytes, mimetype='application/octet-stream')

    except Exception as e:
        print(f"[SERVER] Exceptie fatala: {str(e)}")
        return f"Exceptie server: {str(e)}", 200
