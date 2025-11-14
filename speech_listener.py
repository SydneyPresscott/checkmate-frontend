import speech_recognition as sr

def listen_for_command():
    """
    Listens for a single command from the user's microphone
    and returns the transcribed text.
    """
    # 1. Initialize the recognizer
    recognizer = sr.Recognizer()
    
    # 2. Use the default microphone as the audio source
    with sr.Microphone() as source:
        
        # --- Adjust for ambient noise ---
        # This is a critical step to improve accuracy.
        # It listens for 1 second to learn the "noise level".
        print("\n[Check Mate 👂]: Calibrating for ambient noise...")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        
        print("[Check Mate 👂]: Listening... Speak your command.")
        
        try:
            # --- 3. Listen for audio ---
            # This blocks the code until the user stops speaking.
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            
            # --- 4. Transcribe audio ---
            # Use Google's free web-speech API to transcribe.
            print("[Check Mate 👂]: Processing speech...")
            text = getattr(recognizer, "recognize_google")(audio)
            text = text.lower() # Convert to lowercase
            
            print(f"[Check Mate 👂]: Heard: '{text}'")
            return text

        except sr.WaitTimeoutError:
            print("[Check Mate 👂]: Listening timed out. No speech detected.")
            return None
        except sr.UnknownValueError:
            print("[Check Mate 👂]: Sorry, I couldn't understand that.")
            return None
        except sr.RequestError as e:
            print(f"[Check Mate 👂]: Could not request results; {e}")
            return None

# --- Test Block ---
if __name__ == "__main__":
    """
    This block runs ONLY when you execute this file directly.
    It's for testing our speech listener.
    """
    print("--- Check Mate Ears Test ---")
    print("You will be asked to speak. Say something.")
    
    command = listen_for_command()
    
    if command:
        print(f"\nTest successful. Final command: {command}")
    else:
        print("\nTest failed or no audio received.")