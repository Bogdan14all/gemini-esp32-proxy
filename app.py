import os
import base64
import json
import requests
from fastapi import FastAPI, Request, Response

app = FastAPI()
API_KEY = os.environ.get("GEMINI_API_KEY", "")

@app.get("/")
def health_check():
    return "Gemini TTS Proxy is running!"

@app.post("/voice")
async def voice_endpoint(request: Request):
    try:
        # 1. Primim audio-ul brut de la ESP32
        audio_bytes = await request.body()
        if len(audio_bytes) < 1000:
            return "Prea putin audio", 400

        print(f"[SERVER] Primit {len(audio_bytes)} bytes de la ESP32.")

        # 2. Trimitem la Gemini pentru transcriere (Speech-to-Text)
        stt_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key=" + API_KEY
        stt_payload = {
            "contents": [{
                "parts": [
                    {"text": "Transcrie exact ce se aude in acest audio. Returneaza doar textul, fara introduceri."},
                    {"inlineData": {"mimeType": "audio/pcm;rate=16000", "data": base64.b64encode(audio_bytes).decode('utf-8')}}
                ]
            }]
        }

        print("[SERVER] Se trimite la Gemini STT...")
        stt_response = requests.post(stt_url, json=stt_payload, timeout=30)
        
        if stt_response.status_code != 200:
            print(f"[SERVER] Eroare STT: {stt_response.status_code}")
            return f"Eroare STT: {stt_response.status_code}", 500

        stt_json = stt_response.json()
        parts = stt_json.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        text_input = "Nu am inteles."
        for part in parts:
            if "text" in part:
                text_input = part["text"]
                break

        print(f"[SERVER] Transcriere: {text_input}")

        # 3. Trimitem textul la Gemini TTS pentru a genera vocea
        tts_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash-tts:generateContent?key=" + API_KEY
        tts_payload = {
            "contents": [{
                "parts": [{"text": f"Spune urmatorul text pe un ton natural: {text_input}"}]
            }],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Puck"}}
                }
            }
        }

        print("[SERVER] Se trimite la Gemini TTS...")
        tts_response = requests.post(tts_url, json=tts_payload, timeout=30)

        if tts_response.status_code != 200:
            print(f"[SERVER] Eroare TTS: {tts_response.status_code}")
            return f"Eroare TTS: {tts_response.status_code}", 500

        tts_json = tts_response.json()
        audio_out_b64 = None
        parts = tts_json.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        for part in parts:
            if "inlineData" in part:
                audio_out_b64 = part["inlineData"]["data"]
                break

        if not audio_out_b64:
            return "Gemini TTS nu a trimis audio", 500

        # 4. Returnăm audio-ul generat către ESP32
        audio_out_bytes = base64.b64decode(audio_out_b64)
        print(f"[SERVER] Succes! Trimit {len(audio_out_bytes)} bytes inapoi.")
        return Response(audio_out_bytes, mimetype='application/octet-stream')

    except Exception as e:
        print(f"[SERVER] Eroare: {e}")
        return f"Eroare server: {str(e)}", 500
