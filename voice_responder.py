import os
from gtts import gTTS
from playsound import playsound

# A temporary file to store the audio response
AUDIO_FILE = "response.mp3"

def speak(text: str):
    """
    Converts text to speech and plays it.
    """
    if not text:
        return

    try:
        # --- 1. Log to console ---
        # This is great for debugging
        print(f"[Check Mate 🗣️]: {text}")

        # --- 2. Generate Speech ---
        # Create the gTTS object
        # We'll use tld='com' for US English, which might sound faster
        tts = gTTS(text=text, lang='en', tld='com', slow=False)
        
        # Save the speech to our temporary file
        tts.save(AUDIO_FILE)
        
        # --- 3. Play Speech ---
        # Play the saved mp3 file
        playsound(AUDIO_FILE)

    except Exception as e:
        print(f"Error in speech module: {e}")
        
    finally:
        # --- 4. Clean Up ---
        # Delete the temporary file after playing
        if os.path.exists(AUDIO_FILE):
            os.remove(AUDIO_FILE)

# --- Test Block ---
if __name__ == "__main__":
    """
    This block runs ONLY when you execute this file directly.
    It's for testing our speech function.
    """
    print("--- Check Mate Voice Test ---")
    print("You should hear the system speak (US Accent).")
    
    speak("Hello, buddy. This is a test of the Check Mate voice responder.")
    speak("All systems are nominal.")