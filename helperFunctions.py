import json
import os
import threading
from dotenv import load_dotenv
from fastapi import WebSocket, WebSocketDisconnect, WebSocketException
from queue import Queue as ThreadQueue
from asyncio import Queue as AsyncQueue
from murf import Murf
import logging
import asyncio
from master_of_ceremony import agent


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



logger = logging.getLogger(__name__)

async def receive_from_websocket(websocket: WebSocket, audio_queue: ThreadQueue, text_queue: AsyncQueue, stop_event: threading.Event):
    try:
        while not stop_event.is_set():
            try:
                message = await websocket.receive()
                print(message)
                if message["type"] == "websocket.receive":
                    if "bytes" in message:
                        audio_queue.put(message["bytes"])
                    elif "text" in message:

                        try:
                            data = json.loads(message["text"])
                            print(data)
                            if 'phase' in data:

                                data_phase = data["phase"]
                                print(data_phase)
                                if data_phase == "initiate":
                                    asyncio.create_task(run_ceremony_agent(websocket, text_queue, audio_queue))
                                    
                            else:
                                print("putting data in text queue!")
                                await text_queue.put(data)
                        except json.JSONDecodeError:
                            print(f"❌ Invalid JSON received: {message['text']}")
                            continue
            
            except WebSocketDisconnect:
                print("❌ WebSocketDisconnect raised - client disconnected.")
                break

            except Exception as e:
                print(f"Some error occured while receiving websocket messages: {e}")
                break
    except Exception as e:
        print(f"Websocket receive failed: {e}")
        stop_event.set()


async def run_ceremony_agent (websocket, text_queue, audio_queue):
    """Run agent without affecting main receiver"""

    try: 
        await agent.ainvoke({
            'websocket': websocket,
            'text_queue': text_queue,
            'audio_queue': audio_queue,
            'event_name':" ",
            'theme':" ",
            'venue':" ",
            'time':" ",
            'purpose':" ",
            "current_speaker_id": 0,
            'speakers_names': [],
            "current_speaker_remarks": " ",
            "ceremony_summary": " ",
            'speakers_data': [],
            "phase": "prepare",
        })

    except WebSocketDisconnect:
        logger.warning("🛑 WebSocket disconnected by client (tab closed, reloaded, etc).")

    except asyncio.CancelledError:
        logger.info("Agent task was cancelled")
    
    except Exception as e:
        logger.error(f"Graph execution failed: {e}")
        
        error_data = {
            "type" :"error",
            "message":"Ceremony interrupted due to technical issues",
            "error": f"Error: {e}"
        }
        await websocket.send_text(json.dumps(error_data))
    