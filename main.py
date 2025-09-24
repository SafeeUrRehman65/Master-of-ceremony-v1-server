import asyncio
import json
from math import e
import threading
from queue import Queue as ThreadQueue
from asyncio import Queue as AsyncQueue
from tkinter import E
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, WebSocketException
from helperFunctions import  receive_from_websocket 
import logging
from master_of_ceremony import agent


logger = logging.getLogger(__name__)

app = FastAPI()

@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print(f'✅ Connection established with frontend websocket successfully!')

    # create the shared queues
    audio_queue = ThreadQueue()
    text_queue = AsyncQueue()
    stop_event = threading.Event()

    try:
        await receive_from_websocket(websocket, audio_queue, text_queue, stop_event) 
    except WebSocketDisconnect as e:
        print(f"❌ WebSocket disconnected by client — Code={e.code}")
    except Exception as e:
        print(f"some error occured while initiating receive {E}")
    
    else:
        print("✅ WebSocket handler completed cleanly")
    