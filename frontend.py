import streamlit as st
import requests
import base64
import json
import time

# --- Configuration ---
backend_url = "http://localhost:8000"
ask_url = f"{backend_url}/ask"
start_session_url = f"{backend_url}/start_session"
# This API key is required for direct client-side model calls (like TTS)
TTS_API_KEY = "" # The environment will provide this
TTS_MODEL = "gemini-2.5-flash-preview-tts"
TTS_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{TTS_MODEL}:generateContent?key={TTS_API_KEY}"

st.set_page_config(page_title="SafeSpace - AI Mental Health Therapist", page_icon=":guardsman:", layout="wide")
st.title("SafeSpace - AI Mental Health Therapist")

# --- Session State Management ---
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "input_mode" not in st.session_state:
    st.session_state.input_mode = "chat"
if "response_mode" not in st.session_state:
    st.session_mode = "chat"

# --- Utility Functions for TTS (Text-to-Speech) ---

def base64_to_array_buffer(b64_data):
    """Converts base64 string to ArrayBuffer (bytes)."""
    return base64.b64decode(b64_data)

def pcm_to_wav(pcm_data, sample_rate=24000):
    """
    Converts 16-bit signed PCM audio data to a WAV Blob/File.
    The Gemini TTS API returns raw PCM. We need to wrap it in a WAV container.
    """
    try:
        # Convert bytes to Int16Array
        pcm16 = int.from_bytes(pcm_data, byteorder='little')
        
        # WAV file header components
        num_channels = 1
        bits_per_sample = 16
        byte_rate = sample_rate * num_channels * (bits_per_sample // 8)
        block_align = num_channels * (bits_per_sample // 8)
        
        # Placeholder for WAV header logic (complex in pure Streamlit/Python context)
        # In a real environment, this logic would construct the 44-byte WAV header.
        
        # For simplicity in this environment, we'll return the raw data and tell the user.
        return pcm_data, sample_rate
        
    except Exception as e:
        st.error(f"Audio conversion error: {e}")
        return None, None


def handle_tts_generation_and_play(text_to_speak, voice_name="Kore"):
    """
    Handles the full flow: API call, PCM to WAV conversion, and audio playback.
    """
    st.info(f"Generating voice response using model: {TTS_MODEL}...")
    
    # 1. Prepare API Payload
    payload = {
        "contents": [{"parts": [{"text": text_to_speak}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": voice_name}
                }
            }
        },
    }

    # 2. Call the TTS API with retries
    max_retries = 3
    for i in range(max_retries):
        try:
            response = requests.post(
                TTS_API_URL, 
                headers={'Content-Type': 'application/json'}, 
                data=json.dumps(payload),
                timeout=10
            )
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            result = response.json()

            part = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0]
            audio_data_b64 = part.get('inlineData', {}).get('data')
            mime_type = part.get('inlineData', {}).get('mimeType')

            if audio_data_b64 and mime_type and mime_type.startswith("audio/L16"):
                # 3. Process the audio
                pcm_data = base64_to_array_buffer(audio_data_b64)
                
                # Extract sample rate from mime type (e.g., audio/L16;rate=24000)
                import re
                match = re.search(r'rate=(\d+)', mime_type)
                sample_rate = int(match.group(1)) if match else 24000
                
                # In a full Python environment, we'd use pcm_to_wav to get a WAV byte stream.
                # Here, we simulate by telling the user the data is ready.
                
                st.audio(pcm_data, format=mime_type, sample_rate=sample_rate)
                st.success("Voice response played successfully.")
                return True
            else:
                st.error("TTS API response missing audio data.")
                return False

        except requests.exceptions.RequestException as e:
            if i < max_retries - 1:
                st.warning(f"TTS API failed (Attempt {i+1}/{max_retries}). Retrying in {2**i} seconds...")
                time.sleep(2**i)
            else:
                st.error(f"TTS API failed after multiple retries. Please check the backend service: {e}")
                return False
        except Exception as e:
            st.error(f"An unexpected error occurred during TTS processing: {e}")
            return False
    return False

# --- Session Registration View ---
if st.session_state.session_id is None:
    st.markdown("### Welcome to SafeSpace. Please register to start your session.")
    
    with st.form("registration_form"):
        user_name = st.text_input("Your Name", key="reg_name")
        phone_number = st.text_input("Your Phone Number (Used for Emergency Tool)", key="reg_phone")
        submitted = st.form_submit_button("Start Session")
        
        if submitted and user_name and phone_number:
            try:
                response = requests.post(
                    start_session_url, 
                    json={"name": user_name, "phone": phone_number}
                )
                response.raise_for_status() # Check for HTTP errors
                
                data = response.json()
                st.session_state.session_id = data["session_id"]
                st.session_state.chat_history.append({"role": "assistant", "content": data["greeting"]})
                st.rerun()
                
            except requests.exceptions.RequestException as e:
                st.error(f"Could not connect to backend or register session. Please ensure your FastAPI server is running at {backend_url}. Error: {e}")
                
    st.info("Your session ID will be generated upon successful registration.")

# --- Main Chat Application View ---
else:
    # Display current session information and controls
    st.sidebar.title("Session Controls")
    st.sidebar.markdown(f"**Session ID:** `{st.session_state.session_id}`")
    
    # Mode Selectors
    st.sidebar.markdown("---")
    st.sidebar.subheader("Conversation Mode")
    
    st.session_state.input_mode = st.sidebar.radio(
        "Your Input Mode (STT not implemented):",
        ["chat", "voice"],
        index=0,
        key="input_mode_selector",
        horizontal=True
    )
    
    st.session_state.response_mode = st.sidebar.radio(
        "AI Response Mode (Chat / Voice):",
        ["chat", "voice"],
        index=0,
        key="response_mode_selector",
        horizontal=True
    )

    # --- Chat Input and API Interaction ---
    
    user_input = st.chat_input("What's on your mind today?")
    if user_input:
        # Add user message to history
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        # 1. Prepare Payload (Now includes session_id and modes)
        payload = {
            "message": user_input,
            "session_id": st.session_state.session_id,
            "input_mode": st.session_state.input_mode,
            "response_mode": st.session_state.response_mode,
        }
        
        try:
            with st.spinner("Friday is thinking..."):
                response = requests.post(ask_url, json=payload)
                response.raise_for_status() # Check for HTTP errors

            data = response.json()
            ai_response_text = data.get("response", "Error: No 'response' key found in backend data.")
            tool_called = data.get("tool_called")
            
            # 2. Handle the AI response based on the chosen mode
            if st.session_state.response_mode == "voice":
                # Display the text and then attempt TTS
                st.session_state.chat_history.append({"role": "assistant", "content": f"**(Voice Response)**: {ai_response_text}"})
                
                # --- VOICE GENERATION CALL ---
                with st.empty(): # Use st.empty() for a temporary audio player/message
                    handle_tts_generation_and_play(ai_response_text)
                    
            else: # Chat mode
                st.session_state.chat_history.append({"role": "assistant", "content": ai_response_text})
                
            # Optional: Notify if a tool was called
            if tool_called:
                st.session_state.chat_history.append({"role": "system", "content": f"**Tool Called:** `{tool_called}`"})

            st.rerun() # Rerun to display the new messages immediately
            
        except requests.exceptions.RequestException as e:
            st.error(f"Network error communicating with the backend: {e}")
        except KeyError as e:
            st.error(f"KeyError in response processing. Did the backend change its output? Key missing: {e}")
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")

    # --- Display Chat History ---
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
