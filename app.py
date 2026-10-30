import os
import asyncio
import traceback
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from google import genai
from google.genai import types

app = FastAPI()
API_KEY = os.environ.get("GEMINI_API_KEY", "")
# Folosim v1beta, endpoint-ul standard pentru Live API
client = genai.Client(api_key=API_KEY, http_options={'api_version': 'v1beta'})

@app.get("/")
def health_check():
    return "Live Proxy is running!"

@app.websocket("/audio_ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("\n[SERVER] ESP32 s-a conectat la WebSocket!")
    
    try:
        print("[SERVER] Se încearcă conectarea la Google Live API...")
        # MODELUL CORECT PENTRU VOCE LIVE
        async with client.aio.live.connect(
            model="models/gemini-live-2.5-flash-native-audio", 
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
            print("[SERVER] >>> CONECTAT CU SUCCES LA GOOGLE LIVE API! <<<")
            
            async def receive_from_esp32():
                while True:
                    try:
                        data = await websocket.receive_bytes()
                        await session.send_realtime_input(
                            media=types.Blob(data=data, mime_type="audio/pcm;rate=16000")
                        )
                    except WebSocketDisconnect:
                        print("[SERVER] ESP32 s-a deconectat.")
                        break
                    except Exception as e:
                        print(f"[SERVER] Eroare trimitere ESP32: {e}")
                        break

            async def receive_from_google():
                while True:
                    try:
                        async for response in session.receive():
                            if response.data:
                                await websocket.send_bytes(response.data)
                    except Exception as e:
                        print(f"[SERVER] Eroare primire Google: {e}")
                        break

            task1 = asyncio.create_task(receive_from_esp32())
            task2 = asyncio.create_task(receive_from_google())
            await asyncio.gather(task1, task2)

    except Exception as e:
        print(f"[SERVER] EROARE FATALA LA CONECTAREA CU GOOGLE:")
        traceback.print_exc()
        try:
            await websocket.send_text(f"EROARE GOOGLE: {str(e)}")
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass
