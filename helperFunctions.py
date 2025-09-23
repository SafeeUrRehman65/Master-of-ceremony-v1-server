import json
import os
import threading
from dotenv import load_dotenv
from fastapi import WebSocket
from queue import Queue as ThreadQueue
from asyncio import Queue as AsyncQueue
from murf import Murf

load_dotenv()
client = Murf(api_key=os.getenv("MURF_AI_API_KEY"))

def text_to_speech(text: str):
    response = client.text_to_speech.generate(
    text = text,
    voice_id = "en-US-ken",
    style = "Promo",
    pitch = 10
    )


    return response.audio_file


async def receive_from_websocket(websocket: WebSocket, audio_queue: ThreadQueue, text_queue: AsyncQueue, stop_event: threading.Event):
    try:
        while not stop_event.is_set():
            try:
                message = await websocket.receive()

                if message["type"] == "websocket.receive":
                    if "bytes" in message:
                        audio_queue.put(message["bytes"])
                    elif "text" in message:
                        try:
                            data = json.loads(message["text"])
                            await text_queue.put(data)
                        except json.JSONDecodeError:
                            print("❌ Invalid JSON received")
            except Exception as e:
                print(f"Some error occured while receiving websocket messages: {e}")
                break
    except Exception as e:
        print(f"Websocket receive failed: {e}")
        stop_event.set()