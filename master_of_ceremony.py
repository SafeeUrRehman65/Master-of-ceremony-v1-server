import asyncio
import json
import os
import queue
import threading
from langchain.output_parsers import PydanticOutputParser
from text_to_speech import text_to_speech
from errorHandler import node_error_handler 
import logging
from langchain_community.document_loaders import PyPDFLoader
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from classes.transcriptionClient import TranscriptionClient
from prompts import ceremony_initiater_prompt, script_output_prompt, speaker_introduction_prompt, speaker_remark_prompt, ceremony_end_prompt, script_extraction_prompt
from textstat import textstat
from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate
from langchain_fireworks import ChatFireworks
from schemas import script_json_schema
from schemas import Script, State, Remarks, script_json_schema

load_dotenv()
llm = ChatFireworks(
    api_key = os.getenv("FIREWORKS_API_KEY"),
    temperature=0,
    model="accounts/fireworks/models/kimi-k2-instruct-0905",
)

# /fireworks/models/deepseek-v3p1
# /fireworks/models/gpt-oss-120b
# /fireworks/models/kimi-k2-instruct-0905

current_state = {
    "type": "current_state",
    "message":" ",
    "phase": " "
}

parser = PydanticOutputParser(pydantic_object= Script)

# bind llm with structured output for extracting information from script
llm_with_structured_output = llm.with_structured_output(script_json_schema, include_raw = True)


loader = PyPDFLoader("context/BOE_Agenda.pdf")
pages = loader.load_and_split()

boe_agenda_text = " ".join(list(map(lambda page: page.page_content, pages))) 


logger = logging.getLogger(__name__)

# Nodes
# start the ceremony
@node_error_handler
async def read_script(state: State):
    """Read the script and produce structured outputs"""
    
    # prompt = ChatPromptTemplate.from_messages([
    #     ("system", script_output_prompt)
    # ]).partial(format_instructions = parser.get_format_instructions())
    prompt = ChatPromptTemplate.from_messages([
    ("system", script_extraction_prompt)
    ])
    current_state["message"] = "📜 Reading script to extract ceremony information..."

    await state["websocket"].send_text(json.dumps(current_state))

    
    chain = prompt | llm

    response = chain.invoke({"script": boe_agenda_text})

    if response is None:
        print(f"🟥 No structured output parsed from given script!")
        goto = END

        return Command(goto = goto, update = {})

    print("script with structured outputs", response.content)
    # overwrite response
    response = json.loads(response.content)
    if (len(response["speakers_names"]) == 0 or len(response["speakers_data"]) == 0):
        print(f"🟥 There is no speakers data in the script so ending MoC agent")
        goto = END
        # pass empty_list as there is no speakers data in the script
        updated_message = {}
        return Command(goto = goto, update = updated_message)

    updated_message = {
        "event_name" : response["event_name"],
        'theme' : response["theme"],
        'venue' : response["venue"],
        'time' : response["time"],
        'purpose' : response["purpose"],
        'speakers_names' : response["speakers_names"],
        'speakers_data' : response["speakers_data"]
    }
    print(f"Ceremony data extracted from the script: {updated_message}")

    # send ceremony information to frontend
    response_data = { **updated_message, "type":"ceremony_data" }
    await state["websocket"].send_text(json.dumps(response_data))

    return updated_message


@node_error_handler
async def initiate_ceremony(state: State):
    """Initiate the ceremony"""
    
    current_state["message"] = "Initiating Ceremony ..."
    await state["websocket"].send_text(json.dumps(current_state))

    state["phase"] = "initiate"


    prompt = ChatPromptTemplate.from_messages([
        ("system", ceremony_initiater_prompt),
    ])
    
    chain = prompt | llm
    response = chain.invoke({"event_name": state["event_name"], "theme": state["theme"], "venue": state["venue"], "time": state["time"], "purpose": state["purpose"]})
    audio_url = text_to_speech(response.content)
    response_data = {
        "type": "audio_url",
        "phase": "initiate",
        "audio_url": audio_url
    }

    # empty the queue
    while not state["text_queue"].empty():
        try:
            state["text_queue"].get_nowait()
        except asyncio.QueueEmpty:
            break
    
    await state["websocket"].send_text(json.dumps(response_data))
    
    try:
        while True:
            data = await state["text_queue"].get()
            if data.get("audioFinished"):
                return
            else:
                continue
    except Exception as e:
        logger.error(f"Some error occured while receiving audio flag in initiate ceremony: {e}")

@node_error_handler
async def introduce_speaker(state: State):
    """Introduces the speaker"""
    current_speaker_data = state["speakers_data"][state["current_speaker_id"]]

    
    current_state["message"] = f'👨 Introducing speaker {current_speaker_data["speaker_name"]}...'
    await state["websocket"].send_text(json.dumps(current_state))

    state["phase"] = "introduce"
    prompt = ChatPromptTemplate.from_messages([
        ("system", speaker_introduction_prompt)
    ])
    
    chain = prompt | llm
    speaker_introduction = chain.invoke({
        "speaker_id" : state["current_speaker_id"],
        "speaker_name": current_speaker_data["speaker_name"], "speaker_designation": current_speaker_data["designation"], "speaker_inspiration": current_speaker_data["inspiration"], "purpose_of_speech": current_speaker_data["purpose_of_speech"], "script_of_speech": current_speaker_data["script_of_speech"]})


    audio_url = text_to_speech(speaker_introduction.content)
    response_data = {
        "type": "audio_url",
        "phase": "introduce",
        "audio_url": audio_url
    }

    # empty the queue
    while not state["text_queue"].empty():
        try:
            state["text_queue"].get_nowait()
        except asyncio.QueueEmpty:
            break
    
    await state["websocket"].send_text(json.dumps(response_data))
    
    try:
        while True:
            data = await state["text_queue"].get()
            if data.get("audioFinished"):
                return
            else:
                continue
    except Exception as e:
        logger.error(f"Some error occured while receiving audio flag in initiate ceremony: {e}")

@node_error_handler
async def listen_to_speaker(state: State):
    """Listens to speaker and detects speech end after every 1 minute"""
    current_speaker_data = state["speakers_data"][state["current_speaker_id"]]
    

    # update current state
    current_state.update({
    "message": f'🎙️ Mr. {current_speaker_data["speaker_name"]}, please hit the Start Speech button to continue', 
    "phase": "listen"
    })
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", speaker_remark_prompt)
    ])
    speakers_script = current_speaker_data["script_of_speech"]

    minutes_of_script = textstat.reading_time(speakers_script, ms_per_char=14.69)
    minutes_of_script_rounded = round(minutes_of_script)

    print(f"{current_speaker_data['speaker_name']}'s script is {minutes_of_script_rounded} min long")

    print(f"Listening to {current_speaker_data['speaker_name']} now")

    # remarks generation interval, after every quarter of time has passed
    # also convert to seconds
    # remark_generation_interval = (minutes_of_script_rounded / 4) * 60
    remarks_speech_detection_llm = llm.with_structured_output(schema = Remarks) 
    chain = prompt | remarks_speech_detection_llm
    if state["websocket"]:
        # initiate a queue to store incoming audio chunks
        
        # empty the audio queue for fresh audio chunks
        while not state["audio_queue"].empty():
            try:
                state["audio_queue"].get_nowait()
            except queue.Empty:
                break

        # Clear stale messages from the text queue
        while not state["text_queue"].empty():
            try:
                state["text_queue"].get_nowait()
            except asyncio.QueueEmpty:
                break

        
        await state["websocket"].send_text(json.dumps(current_state))
        # initiate a new transcription client
        new_client = TranscriptionClient(state["websocket"])    
        # initiate a new client thread to stop prevent effect
        new_client_thread = threading.Thread(target=new_client.run, args=(state["audio_queue"],), daemon=True)

        try:
            while True:
                data = await state["text_queue"].get()
                if data.get("speaking", True):

                    # start the client thread
                    new_client_thread.start()

                    # update current state, notify frontend
                    current_state.update({
                    "message": f"🎙️ Listening to Mr/Ms. {current_speaker_data['speaker_name']}'s speech"
                    })
                    

                    # send currently speaking speaker details to frontend
                    current_speaker_details = {**current_speaker_data, "type": "speaker_details",
                    "current_speaker_id": state["current_speaker_id"],
                    "total_speakers": len(state["speakers_names"])}

                    state["websocket"].send_text(json.dumps(current_speaker_details))

                    print(f"🎤 Speaker {current_speaker_data['speaker_name']} has started the speech.")
                    continue
                    
                elif not data.get("speaking", True):

                    speaker_speech_partial = new_client.state
                    
                    # close the fireworks ai connection
                    new_client.close()

                    new_client_thread.join(timeout=5)
                    # speech ended, generate remarks
                    response = chain.invoke({"speaker_name": current_speaker_data["speaker_name"], "speaker_designation": current_speaker_data["designation"], "purpose_of_speech": current_speaker_data["purpose_of_speech"], "speech": speaker_speech_partial})

                    print(f"Speaker stopped speaking", response)

                    update = {
                        "current_speaker_remarks" : response.remarks
                    }
                    
                    return update
                else:
                    # user hasn't clicked the speech control button yet
                    continue    
        except Exception as e:
            logger.error(f"Some error occured in listen to speaker: {e}")

@node_error_handler                    
async def give_remarks(state: State):
    """Play the given remarks and route to the correct node"""

    state["phase"] = "remarks"
    current_speaker = state["speakers_data"][state["current_speaker_id"]]
    current_state["message"] = f'Giving remarks to speaker{current_speaker["speaker_name"]}...'
    await state["websocket"].send_text(json.dumps(current_state))
    speaker_remarks = state["current_speaker_remarks"]
    try:
        if speaker_remarks:
            try:
                audio_url = text_to_speech(speaker_remarks)

            except Exception as e:
                print(f"Some error occured while generating speech: {e}")                
            response_data = {
                "type": "audio_url",
                "phase": "remarks",
                "audio_url": audio_url
            }

            # Clear stale messages from the text queue
            while not state["text_queue"].empty():
                try:
                    state["text_queue"].get_nowait()
                except asyncio.QueueEmpty:
                    break

            await state["websocket"].send_text(json.dumps(response_data))
            try:
                while True:
                    data = await state["text_queue"].get()
                    if data.get("audioFinished"):
                        if ( (len(state["speakers_names"]) - 1 ) >= (state["current_speaker_id"] + 1)):
                            new_speaker_id = state["current_speaker_id"] + 1

                            print("current speaker id", new_speaker_id)
                            print(f"Introduce the next speaker")
                            update = {
                                "current_speaker_id" : new_speaker_id
                            }
                            goto = "introduce_speaker"
                            return Command(goto = goto, update=update)
                        else:
                            print(f"All speeches delivered. End the ceremony")
                            goto = "end_ceremony"
                            return Command(goto = goto)
                    else:
                        continue  
            except Exception as e:
                logger.error(f"Some error occured in give_remarks: {e}")

        else:
            print("""Speaker remarks are empy.
            ❌ Cant play audio""")
    except Exception as error:
        print(f"Some error occured while sending audio url to frontend: {error}")

@node_error_handler
async def end_ceremony(state: State):
    """Provide graceful remarks to end ceremony"""
    
    state["phase"] = "end"

    current_state["message"] = "🎉 Ending the ceremony, thank you for attending the event..."
    await state["websocket"].send_text(json.dumps(current_state))
    prompt = ChatPromptTemplate.from_messages([
        ("system", ceremony_end_prompt)
    ])

    chain = prompt | llm

    ending_remarks = chain.invoke({"speakers_data": state["speakers_data"], "event_name": state["event_name"], "theme": state["theme"], "venue": state["venue"], "purpose": state["purpose"]})

    try :
        audio_url = text_to_speech(ending_remarks.content)

        response_data = {
            "type": "audio_url",
            "phase": "end",
            "audio_url": audio_url
        }

        # Clear stale messages from the text queue
        while not state["text_queue"].empty():
            try:
                state["text_queue"].get_nowait()
            except asyncio.QueueEmpty:
                break

        await state["websocket"].send_text(json.dumps(response_data))
        try:
            while True:
                data = await state["text_queue"].get()
                if data.get("audioFinished"):
                    return
                else:
                    continue
        except Exception as e:
            logger.error(f"Some error occured in initiate ceremony: {e}")
    except Exception as error:
        print(f"Some error ocurred: {error}")



graph_builder = StateGraph(State)
# orchestrate the workflow
graph_builder.add_node("read_script", read_script)
graph_builder.add_node("initiate_ceremony", initiate_ceremony)
graph_builder.add_node("introduce_speaker", introduce_speaker)
graph_builder.add_node("listen_to_speaker", listen_to_speaker)
graph_builder.add_node("give_remarks", give_remarks)
graph_builder.add_node("end_ceremony", end_ceremony)

graph_builder.add_edge(START, "read_script")
graph_builder.add_edge("read_script", "initiate_ceremony")
graph_builder.add_edge("initiate_ceremony", "introduce_speaker")
graph_builder.add_edge("introduce_speaker", "listen_to_speaker")
graph_builder.add_edge("listen_to_speaker", "give_remarks")

agent = graph_builder.compile()
