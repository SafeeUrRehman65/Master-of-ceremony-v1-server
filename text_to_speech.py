from murf import Murf
import websockets
import json
import base64
from dotenv import load_dotenv
import os

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


