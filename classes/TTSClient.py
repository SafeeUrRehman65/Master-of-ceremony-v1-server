from murf import Murf
import websockets
import json
import base64
from dotenv import load_dotenv
import os


load_dotenv()

API_KEY = os.getenv("MURF_AI_API_KEY") 

WS_URL = "wss://api.murf.ai/v1/speech/stream-input"
# Audio format settings (must match your API output)
SAMPLE_RATE = 44100
CHANNELS = 1


class TTS_Client:
    def __init__(self, frontend_ws):
        self.frontend_ws = frontend_ws
        self.tts_ws = None
        self._is_connected = False #Track connection status
    

    async def create_tts_connection(self):
        """Initiate websocket connection with TTS Service"""
        self.tts_ws = await websockets.connect(
            f"{WS_URL}?api-key={API_KEY}&sample_rate=44100&channel_type=MONO&format=MP3"
        )
        print(f'TTS websocket connection established successfully')

        # Send voice config first (optional)
        voice_config_msg = {
            "voice_config": {
                "voiceId": "en-US-ken",
                "style": "Promo",
                "rate": 0,
                "pitch": 6,
                "variation": 1
            }
        }
        self._is_connected = True
        
        print(f'Sending payload : {voice_config_msg}')
        await self.tts_ws.send(json.dumps(voice_config_msg))

    async def close_tts_connection(self):
        """Close the TTS websocket connection gracefully"""
        if self.tts_ws and self._is_connected:
            try:
                # close the websocket connection
                await self.tts_ws.close()
                print("TTS websocket connection closed successfully")

            except Exception as e:
                print(f"Error closing websocket: {e}")
            finally:
                self._is_connected = False
                self.tts_ws = None

    async def send_text_to_murf(self, transcription):
        """Send transcription to Murf for TTS"""
        # Send text in one go (or chunk if you want streaming)
        if not self.tts_ws and self._is_connected:
            raise Exception("TTS Connection not established")

        text_msg = {
            "text": transcription,
            "end" : True # This will close the context. So you can re-run and concurrency is available.
        }
        print(f'Sending payload : {text_msg}')
        if self.tts_ws:

            try:
                await self.tts_ws.send(json.dumps(text_msg))
                try:
                    await self.stream_audio_to_frontend()
                except Exception as e:
                    print(f"Some error occured while streaming audio to frontend: {e}")
                    
            except Exception as e:
                print(f"Some error occured while sending text to Murf TTs service: {e}")
            

    async def stream_audio_to_frontend(self):
        """stream received audio to frontend"""

        if not self._is_connected:
            raise Exception("TTS Connection not established")
        
        if not self.frontend_ws:
            raise Exception("Frontend websocket connection is not established - can't proceed")

        if self.tts_ws:

            try:
                while True:
                    response = await self.tts_ws.recv()
                    data = json.loads(response)
                    

                    if data.get("final"):
                        print(f'Received final flag:  {data}')
                        finish_msg = {
                            "type": "audioFinished"
                        }
                        await self.frontend_ws.send_text(json.dumps(finish_msg))

                        break
                        
                    if "audio" in data:
                        audio_bytes = data["audio"]
                            
                        audio_data = {
                            "type": "audio_chunk",
                            "audio_chunk": audio_bytes
                        }
                        await self.frontend_ws.send_text(json.dumps(audio_data))
                    
            except websockets.exceptions.ConnectionClosed:
                print("TTS connection closed during audio reception")
                self._is_connected = False
            except Exception as e:
                print(f"Some error occured while receiving audio: {e}")
