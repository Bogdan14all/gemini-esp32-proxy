import os
import asyncio
import base64
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from google import genai
from google.genai import types

app = FastAPI()
API_KEY = os.environ.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=API_KEY, http_options={'api_version': 'v1alpha'})

@app.get("/")
def health_check():
    return "Live Proxy is running!"

@app.websocket("/audio_ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("\n[SERVER] ESP32 s-a conectat la WebSocket!")
    
    try:
        # Ne conectăm la Google Live API
        async with client.aio.live.connect(
            model="gemini-2.0-flash-exp", 
            config=types.LiveConnectConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Puck")
                    )
                ),
                system_instruction=types.Content(parts=[types.Part(text="Esti un asistent vocal. Raspunde scurt in romana.")])
            )
        ) as session:
            print("[SERVER] Conectat la Google Live API!")
            
            async def receive_from_esp32():
                while True:
                    try:
                        data = await websocket.receive_bytes()
                        # Trimitem audio-ul brut (PCM 16kHz) direct la Google
                        await session.send_realtime_input(
                            media=types.Blob(data=data, mime_type="audio/pcm;rate=16000")
                        )
                    except WebSocketDisconnect:
                        print("[SERVER] ESP32 deconectat.")
                        break
                    except Exception as e:
                        print(f"[SERVER] Eroare ESP32: {e}")
                        break

            async def receive_from_google():
                while True:
                    try:
                        async for response in session.receive():
                            if response.data:
                                # Trimitem sunetul primit de la Google inapoi la ESP32
                                await websocket.send_bytes(response.data)
                    except Exception as e:
                        print(f"[SERVER] Eroare Google: {e}")
                        break

            # Rulam ambele bucle simultan
            task1 = asyncio.create_task(receive_from_esp32())
            task2 = asyncio.create_task(receive_from_google())
            await asyncio.gather(task1, task2)

    except Exception as e:
        print(f"[SERVER] Eroare fatala: {e}")
    finally:
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
