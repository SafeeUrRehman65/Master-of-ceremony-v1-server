import io
import os
from socket import timeout
import requests
import json
import threading
import time
from queue import Empty
import websocket
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

# Configuration
WEBSOCKET_URL = "wss://audio-streaming.us-virginia-1.direct.fireworks.ai/v1/audio/transcriptions/streaming"
TARGET_SAMPLE_RATE = 16000
CHUNK_SIZE_MS = 50
LANGUAGE = "en"


class TranscriptionClient:
    """Handles real-time audio transcription via WebSocket streaming."""

    def __init__(self, frontend_websocket):
        self.state = {}
        self.segments = {}
        self.frontend_ws = frontend_websocket
        self.lock = threading.Lock()
        self.fireworks_ws = None
        self.audio_chunks = []
        self.stop_event = threading.Event()  # New stop event
        self.streaming_thread  = None

    def stream_audio_to_fireworks(self, ws, queue):
        """Stream audio chunks to the WebSocket."""
        print("Starting audio stream...")

        while not self.stop_event.is_set():
            try:
                chunk = queue.get(timeout=10)
                self.fireworks_ws.send(chunk, opcode = websocket.ABNF.OPCODE_BINARY)
                time.sleep(0.05)
            except Empty:
                print(f"No audio received for 10s. Waiting...")
                continue
            except Exception as error:
                print(f"Some error occured while sending audio chunk to fireworks: {error}")
        print("Audio streaming thread stopped.")

    def on_websocket_open(self, ws, queue):
        """Handle WebSocket connection opening."""
        print("WebSocket connected - starting audio stream")
        # Start streaming in a separate thread
        self.streaming_thread = threading.Thread(
            target=self.stream_audio_to_fireworks,
            args=(ws, queue),
            daemon=True
        )
        self.streaming_thread.start()
        
        

    def on_websocket_message(self, ws, message):
        """Handle incoming transcription messages."""
        try:
            data = json.loads(message)

            # Check for final trace completion
            if data.get("trace_id") == "final":
                print("\nTranscription complete!")
                ws.close()
                return

            # Update transcription state
            if "segments" in data:
                with self.lock:

                    self.segments =  {segment["id"]: segment["text"] for segment in data["segments"]}
                    self.state = ' '.join(self.segments.values())
                    self.send_and_display_transcription()

        except json.JSONDecodeError:
            print(f"Failed to parse message: {message}")

    @staticmethod
    def on_websocket_error(_, error):
        """Handle WebSocket errors."""
        print(f"WebSocket error: {error}")

    def send_and_display_transcription(self):
        """Display the ongoing transcription state."""
        print("\n--- Current Transcription ---")
        print(self.state)
        # send the current state to frontend websocket
        data = {"type": "transcription", "transcription": self.state}
        self.frontend_ws.send_text(json.dumps(data))
        print("----------------------------\n")

    def create_websocket_connection(self, queue):
        """Create and configure the WebSocket connection."""
        # Build WebSocket URL with parameters
        params = urllib.parse.urlencode({"language": LANGUAGE})
        full_url = f"{WEBSOCKET_URL}?{params}"

        api_key = os.getenv("FIREWORKS_API_KEY")
        if not api_key:
            raise ValueError("FIREWORKS_API_KEY environment variable not set")

        
        websocket_client = websocket.WebSocketApp(
            full_url,
            header={"Authorization": api_key},
            on_open= lambda ws: self.on_websocket_open(ws, queue),
            on_message=self.on_websocket_message,
            on_error=self.on_websocket_error,
        )
        self.fireworks_ws = websocket_client

        return websocket_client

    def run(self, queue):
        """Main execution flow."""
        try:
            websocket_client = self.create_websocket_connection(queue)

            print("Connecting to transcription service...")
            websocket_client.run_forever()

        except Exception as e:
            print(f"Error: {e}")
            return 1

        return 0

    def close(self):
        """Stop streaming and close the websocket gracefully"""
        print('Closing transcription client...')

        self.stop_event.set()
        if self.fireworks_ws:
            try:
                self.fireworks_ws.close()
            except Exception as e:
                print(f'Error closing WebSocket: {e}')
        if self.streaming_thread:
            try:
                self.streaming_thread.join()
            except Exception as e:
                print(f"Error joining streaming thread: {e}")
        print("Transcription client closed.")
