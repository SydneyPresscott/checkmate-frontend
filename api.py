import os
import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, BackgroundTasks # <-- FIX: Import BackgroundTasks
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from elevenlabs.client import ElevenLabs # <-- FIX: Corrected import
import requests
import json
import base64
import re
import uuid 
import shutil
import time 

# --- Import our core modules ---
import database_manager # type: ignore
import nlu_parser

# --- Load API Key & Config ---
load_dotenv() 
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# (Removed unused Agora and URL variables)

if not GOOGLE_API_KEY or not ELEVENLABS_API_KEY:
    print("FATAL ERROR: Missing required API keys in .env file.")
    exit()

# --- Initialize Clients ---
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
# --- FIX: Configure the Gemini client and use a valid model name ---
genai_client = genai.GoogleGenerativeAI(api_key=GOOGLE_API_KEY) # type: ignore
gemini_model = genai_client.GenerativeModel('gemini-1.5-flash') # Use a valid, modern model

app = FastAPI()
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# Setup the database on startup
database_manager.setup_database()


# --- ALL API REQUEST MODELS (Defined at the top for clarity) ---
class InsightsRequest(BaseModel):
    stockList: str

class PromoRequest(BaseModel):
    promoIdea: str
    tone: str

class CommandRequest(BaseModel):
    text: str

# --- Conversation "Memory" (Placeholder) ---
conversation_state = {}

# --- FIX: Create a helper function for file cleanup ---
def cleanup_file(file_path: str):
    """Safely removes a file from the filesystem."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"Error cleaning up file {file_path}: {e}")

# ==================================
# === CORE VOICE COMMAND ENDPOINT ===
# ==================================

@app.post("/process-command")
# --- FIX: Inject BackgroundTasks ---
async def process_command(request: CommandRequest, background_tasks: BackgroundTasks):
    global conversation_state
    
    text = request.text.lower().strip()
    
    if not text:
        return {"response": "Sorry, I didn't catch that."}
    
    # --- FIX: Integrate your NLU and Database logic ---
    response_text = ""
    try:
        # 1. Parse the text into a structured command
        # e.g., {"intent": "CHECK_STOCK", "item": "milk"}
        command = nlu_parser.parse_voice_command(text) # pyright: ignore[reportAttributeAccessIssue]
        
        # 2. Execute the command using the database manager
        # This function will run the database query and return a string
        response_text = database_manager.execute_command(command)
        
    except Exception as e:
        print(f"Error processing command: {e}")
        response_text = "Sorry, I ran into an error. Please try again."
    # --- End of logic integration ---

    
    # --- 2. Generate Audio and Return File ---
    temp_file_name = f"response_{uuid.uuid4()}.mp3"
    
    try:
        # 3a. Generate audio using ElevenLabs REST API (use HTTP if SDK doesn't expose a generator)
        #  - Fetch voices and find the voice id for "Rachel" (fallback to first voice)
        voices_resp = requests.get(
            "https://api.elevenlabs.io/v1/voices",
            headers={"xi-api-key": ELEVENLABS_API_KEY}
        )
        voices_resp.raise_for_status()
        voices_json = voices_resp.json()
        voice_id = None
        for v in voices_json.get("voices", []):
            # some API versions return 'voice_id' or 'id'
            if v.get("name") == "Rachel":
                voice_id = v.get("voice_id") or v.get("id")
                break
        if not voice_id and voices_json.get("voices"):
            v0 = voices_json["voices"][0]
            voice_id = v0.get("voice_id") or v0.get("id")

        if not voice_id:
            raise Exception("No ElevenLabs voice available to synthesize audio.")

        synth_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        payload = {
            "text": response_text,
            "model": "eleven_multilingual_v2"
        }

        synth_resp = requests.post(
            synth_url,
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg"
            },
            json=payload,
            stream=True,
        )
        synth_resp.raise_for_status()

        # 3b. Save the audio stream to the temporary file
        with open(temp_file_name, "wb") as f:
            for chunk in synth_resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        # --- FIX: Add the cleanup task to the background queue ---
        background_tasks.add_task(cleanup_file, temp_file_name)
            
        # 3c. Return the file to the frontend
        return FileResponse(
            path=temp_file_name, 
            media_type='audio/mpeg', 
            filename="response.mp3"
            # The incorrect 'background' parameter is now removed
        )
        
    except Exception as e:
        print(f"ElevenLabs Error: {e}")
        # On error, fall back to simple text response
        # This is important so the frontend can still show the text
        return {"response": response_text, "error": "TTS Error"}


# --- Text-based Gemini Endpoints (No change needed, should work now) ---
@app.post("/get-insights")
async def get_insights(request: InsightsRequest):
    system_prompt = "You are Checkmate, a smart inventory assistant..."
    try:
        full_prompt = f"{system_prompt}\n\nUser's stock list: {request.stockList}"
        response = gemini_model.generate_content(full_prompt)
        return {"response": response.text}
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get-promo")
async def get_promo(request: PromoRequest):
    system_prompt = "You are a professional marketing copywriter..."
    user_query = f"Promotion: \"{request.promoIdea}\", Tone: {request.tone}"
    try:
        full_prompt = f"{system_prompt}\n\n{user_query}"
        response = gemini_model.generate_content(full_prompt)
        return {"response": response.text}
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_root():
    return {"message": "Check Mate API is running!"}