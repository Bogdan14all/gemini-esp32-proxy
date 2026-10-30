import os
import base64
import requests
import time
from fastapi import FastAPI, Request, Response

app = FastAPI()
API_KEY = os.environ.get("GEMINI_API_KEY", "")

def request_with_retry(url, payload, timeout=30, max_retries=3):
    for attempt in range(max_retries):
        try:
            res = requests.post(url, json=payload, timeout=timeout)
            
            if res.status_code == 429:
                # Așteptăm 20, 40, 60 de secunde pentru a trece de limita pe minut
                wait_time = 20 * (attempt + 1) 
                print(f"[RETRY] Eroare 429. Limita atinsa. Aștept {wait_time} secunde (încercarea {attempt+1}/{max_retries})...")
                time.sleep(wait_time)
                continue
            
            return res
            
        except requests.exceptions.RequestException as e:
            print(f"[RETRY] Eroare de rețea: {e}. Reîncerc...")
            if attempt == max_retries - 1:
                raise e
            time.sleep(5)
    
    return None

@app.get("/")
def health_check():
    return "Proxy is running!"

@app.post("/voice")
async def voice_endpoint(request: Request):
    try:
        audio_bytes = await request.body()
        if len(audio_bytes) < 1000:
            return Response(content="Audio prea mic", status_code=200, media_type="text/plain")

        print(f"\n[SERVER] Primit {len(audio_bytes)} bytes de la ESP32.")

        # --- 1. SPEECH TO TEXT ---
        print("[SERVER] Se incearca transcrierea (STT)...")
        stt_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key=" + API_KEY
        stt_payload = {
            "contents": [{
                "parts": [
                    {"text": "Transcrie exact ce se aude in acest audio. Returneaza doar textul."},
                    {"inlineData": {"mimeType": "audio/pcm;rate=16000", "data": base64.b64encode(audio_bytes).decode('utf-8')}}
                ]
            }]
        }
        
        stt_res = request_with_retry(stt_url, stt_payload)
        
        if stt_res is None or stt_res.status_code != 200:
            err_code = stt_res.status_code if stt_res else "Timeout/Limita"
            print(f"[SERVER] Eroare STT finala: {err_code}")
            return Response(content=f"Eroare STT: {err_code}", status_code=200, media_type="text/plain")
        
        text_input = stt_res.json()["candidates"][0]["content"]["parts"][0]["text"]
        print(f"[SERVER] Text transcris: {text_input}")

        # --- 2. TEXT TO SPEECH ---
        print("[SERVER] Se incearca generarea vocii (TTS)...")
        tts_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash-tts:generateContent?key=" + API_KEY
        tts_payload = {
            "contents": [{"parts": [{"text": f"Spune clar: {text_input}"}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Puck"}}}
            }
        }

        tts_res = request_with_retry(tts_url, tts_payload)
        
        if tts_res is None or tts_res.status_code != 200:
            err_code = tts_res.status_code if tts_res else "Timeout/Limita"
            print(f"[SERVER] Eroare TTS finala: {err_code}")
            return Response(content=f"Eroare TTS: {err_code}", status_code=200, media_type="text/plain")

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
