from fastapi import WebSocket
from asyncio import Queue as AsyncQueue
import queue
from queue import Queue as ThreadQueue
from threading import Event
from pydantic import BaseModel, Field
from typing import Annotated, ClassVar, List, Literal, Optional, TypedDict

from classes.transcriptionClient import TranscriptionClient
from classes.TTSClient import TTS_Client


# class SpeakerData(BaseModel):
#     speaker_name:str=Field(default=None, description="The name of the speaker")
#     designation: str = Field(default=None, description="The designation of the speaker")
#     inspiration: str = Field(default = None, description = "What inspiration can one draw from the speaker")
#     purpose_of_speech: str = Field(default=None, description='The purpose of the speech')
#     script_of_speech: str = Field(default=None, description='The script of the speaker')

# class SpeakerName(BaseModel):
#     speaker_name:str = Field(default = None, description = "The name of the speaker")

# class Script(BaseModel):
#     """Important details and script of the ceremony"""

#     event_name:str = Field(default = None, description='The name of the event')
#     theme:str = Field(default = None, description='The theme of the event')
#     venue:str = Field(default = None, description='The venue of the event')
#     time:str = Field(default = "06:00 PM", description="The starting time of the event")
#     purpose:str = Field(default = None, description="The purpose/ significance of the event")
#     speakers_names: List[SpeakerName]
#     speakers_data: List[SpeakerData]

class Remarks(BaseModel):
    """Provide remakrs and detects speech"""
    remarks: str = Field(default = None, description="Acknowledgement and complimentary remakrs based on user's speech")

    is_speech: bool = Field(default = False, description="Boolean flag indicating whether speech is present or not")


# initialize state for MoC agent
class State(TypedDict):
    # this state class will hold important information about the ceremony needed for the MoC agent to work smoothly
    websocket: WebSocket
    transcriptionClient: Optional[TranscriptionClient]
    event_name:str 
    theme:str
    venue:str
    time:str
    purpose:str
    current_speaker_id: int
    speakers_names: List
    current_speaker_remarks: str
    ceremony_history: str
    speakers_data: List
    phase: Literal["prepare", "initiate","introduce", "listen", "speeches", "remarks", "honor_sponsors","end"]

    # for centralized communication
    text_queue: AsyncQueue
    audio_queue : ThreadQueue
    stop_event : Event
    class Config:
        arbitrary_types_allowed = True



script_json_schema = {
  "title": "Script",
  "description": "Important details and script of the ceremony",
  "type": "object",
  "properties": {
    "event_name": {
      "type": "string",
      "description": "The name of the event",
      "default": " "
    },
    "theme": {
      "type": "string",
      "description": "The theme of the event",
      "default": " "
    },
    "venue": {
      "type": "string",
      "description": "The venue of the event",
      "default": " "
    },
    "time": {
      "type": "string",
      "description": "The starting time of the event",
      "default": "06:00 PM"
    },
    "purpose": {
      "type": "string",
      "description": "The purpose/ significance of the event",
      "default": " "
    },
    "speakers_names": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "speaker_name": {
            "type": "string",
            "description": "The name of the speaker",
            "default": " "
          }
        },
        "required": ["speaker_name"]
      }
    },
    "speakers_data": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "speaker_name": {
            "type": "string",
            "description": "The name of the speaker",
            "default": " "
          },
          "designation": {
            "type": "string",
            "description": "The designation of the speaker",
            "default": " "
          },
          "inspiration": {
            "type": "string",
            "description": "What inspiration can one draw from the speaker",
            "default": " "
          },
          "purpose_of_speech": {
            "type": "string",
            "description": "The purpose of the speech",
            "default": " "
          },
          "script_of_speech": {
            "type": "string",
            "description": "The script of the speaker",
            "default": " "
          }
        },
        "required": ["speaker_name", "designation", "inspiration", "purpose_of_speech", "script_of_speech"]
      }
    }
  },
  "required": ["event_name", "theme", "venue","time","purpose", "speakers_names", "speakers_data"]
}



class SpeakerName(TypedDict):
    speaker_name: Annotated[str ,..., "The name of the speaker"]


class SpeakerData(TypedDict):
    speaker_name : Annotated[str, ... ,"The name of the speaker"]
    designation : Annotated[str, ... , "The designation of the speaker"]
    inspiration : Annotated[str, ... , "What inspiration can one draw from the speaker"]
    purpose_of_speech : Annotated[str, ... , 'The purpose of the speech']
    script_of_speech : Annotated[str, ... , 'The script of the speaker']



class Script(TypedDict):
    """Important details and script of the ceremony"""

    event_name: Annotated[str, ... ,'The name of the event']
    theme: Annotated[str, ... ,'The theme of the event']
    venue: Annotated[str, ... ,'The venue of the event']
    time: Annotated[str, "06:00 PM" ,"The starting time of the event"]
    purpose: Annotated[str, ... , "The purpose/ significance of the event"]
    speakers_names: List[SpeakerName]
    speakers_data: List[SpeakerData]


