from functools import wraps 
import logging
from fastapi import WebSocketException
import asyncio
import json

logger = logging.getLogger(__name__)

def node_error_handler(func):
    
    @wraps(func)
    async def async_wrapper(state, *args, **kwargs):
        try:
            return await func(state, *args, **kwargs)
        
        except WebSocketException as e :
            logger.error(f"Websocket error in {func.__name__}: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Some error occured while executing {func.__name__}: {e}")
            await send_error_to_frontend(state, f"Error in {func.__name__}", e)
            raise

    @wraps(func)
    def sync_wrapper(state, *args, **kwargs):
        try:
            return func(state, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            asyncio.create_task(send_error_to_frontend(state, f"Error in {func.__name__}", e))
            raise

    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

async def send_error_to_frontend(state, error_message, error):
    try:
        if hasattr(state, 'websocket') and state.websocket:
            frontend_error_data = {"type": "message", "message": error_message, "error": error}

            await state.websocket.send_text(json.dumps(frontend_error_data))
    except Exception as e:
        logger.error(f"Some error occured while sending error data to frontend: {e}")


async def send_error(websocket, message, error):
    error_data = {
            "type" :"error",
            "message": message,
            "error": f"Error: {error}"
    }
    await websocket.send_text(json.dumps(error_data))