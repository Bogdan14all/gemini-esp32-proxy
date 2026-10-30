import os
import base64
import requests
from fastapi import FastAPI, Request, Response

app = FastAPI()
API_KEY = os.environ.get("GEMINI_API_KEY", "")

@app.get("/")
def health_check():
    return "Proxy is running!"

@app.post("/voice")
async def voice_endpoint(request: Request):
    try:
        audio_bytes = await request.body()
        if len(audio_bytes) < 1000:
            print("[SERVER] Eroare: Audio prea mic.")
            return Response(content="Audio prea mic", status_code=200, media_type="text/plain")

        print(f"\n[SERVER] Primit {len(audio_bytes)} bytes de la ESP32.")

        # --- 1. SPEECH TO TEXT (Transcriere) ---
        print("[SERVER] Se incearca transcrierea (STT)...")
        # FOLOSIM MODELUL CORECT PENTRU TEXT
        stt_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key=" + API_KEY
        
        stt_payload = {
            "contents": [{
                "parts": [
                    {"text": "Transcrie exact ce se aude in acest audio. Returneaza doar textul, fara introduceri."},
                    {"inlineData": {"mimeType": "audio/pcm;rate=16000", "data": base64.b64encode(audio_bytes).decode('utf-8')}}
                ]
            }]
        }
        
        stt_res = requests.post(stt_url, json=stt_payload, timeout=30)
        
        if stt_res.status_code != 200:
            print(f"[SERVER] Eroare STT Google: {stt_res.status_code} - {stt_res.text[:100]}")
            return Response(content=f"Eroare STT: {stt_res.status_code}", status_code=200, media_type="text/plain")
        
        text_input = stt_res.json()["candidates"][0]["content"]["parts"][0]["text"]
        print(f"[SERVER] Text transcris: {text_input}")

        # --- 2. TEXT TO SPEECH (Generare Voce) ---
        print("[SERVER] Se incearca generarea vocii (TTS)...")
        tts_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash-tts:generateContent?key=" + API_KEY
        
        tts_payload = {
            "contents": [{"parts": [{"text": f"Spune clar: {text_input}"}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Puck"}}}
            }
        }

        tts_res = requests.post(tts_url, json=tts_payload, timeout=30)
        
        if tts_res.status_code != 200:
            print(f"[SERVER] Eroare TTS Google: {tts_res.status_code} - {tts_res.text[:100]}")
            return Response(content=f"Eroare TTS: {tts_res.status_code}", status_code=200, media_type="text/plain")

        tts_json = tts_res.json()
        audio_out_b64 = tts_json["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
        
        if not audio_out_b64:
            return Response(content="TTS nu a returnat audio", status_code=200, media_type="text/plain")

        audio_out_bytes = base64.b64decode(audio_out_b64)
        print(f"[SERVER] Succes! Se trimit {len(audio_out_bytes)} bytes audio inapoi.")
        
        return Response(content=audio_out_bytes, media_type="application/octet-stream")

    except Exception as e:
        print(f"[SERVER] Exceptie fatala: {str(e)}")
        return Response(content=f"Eroare server: {str(e)}", status_code=200, media_type="text/plain")
