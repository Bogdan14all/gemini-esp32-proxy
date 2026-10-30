import os
import base64
import json
from fastapi import FastAPI, Request
from google.cloud import speech, texttospeech
from google.oauth2 import service_account

app = FastAPI()

# Preluăm credențialele din variabila de mediu (JSON-ul de la Google Cloud)
creds_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
if not creds_json:
    raise ValueError("Lipseste GOOGLE_APPLICATION_CREDENTIALS_JSON")

creds_dict = json.loads(creds_json)
credentials = service_account.Credentials.from_service_account_info(creds_dict)

# Inițializăm clienții STT și TTS
stt_client = speech.SpeechClient(credentials=credentials)
tts_client = texttospeech.TextToSpeechClient(credentials=credentials)

@app.get("/")
def health_check():
    return "Hybrid Voice Proxy is running!"

@app.post("/voice")
async def voice_endpoint(request: Request):
    try:
        # 1. Primim audio-ul brut de la ESP32 (PCM 16kHz)
        audio_bytes = await request.body()
        if len(audio_bytes) < 1000:
            return "Prea putin audio", 400

        print(f"[SERVER] Primit {len(audio_bytes)} bytes de la ESP32.")

        # 2. Trimitem la STT pentru transcriere
        audio = speech.RecognitionAudio(content=audio_bytes)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="ro-RO",
        )

        print("[SERVER] Se trimite la Google STT...")
        stt_response = stt_client.recognize(config=config, audio=audio)
        
        if not stt_response.results:
            print("[SERVER] Nu s-a inteles nimic.")
            return "Nu am inteles.", 200

        text_input = stt_response.results[0].alternatives[0].transcript
        print(f"[SERVER] Transcriere: {text_input}")

        # 3. Trimitem textul la TTS pentru a genera vocea
        synthesis_input = texttospeech.SynthesisInput(text=text_input)
        
        voice = texttospeech.VoiceSelectionParams(
            language_code="ro-RO",
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            sample_rate_hertz=24000
        )

        print("[SERVER] Se trimite la Google TTS...")
        tts_response = tts_client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        # 4. Returnăm audio-ul generat către ESP32
        print(f"[SERVER] Succes! Trimit {len(tts_response.audio_content)} bytes inapoi.")
        return tts_response.audio_content

    except Exception as e:
        print(f"[SERVER] Eroare: {e}")
        return f"Eroare server: {str(e)}", 500
