import streamlit as st
from audio_recorder_streamlit import audio_recorder
import requests
import base64

st.set_page_config(page_title="Voice & Text DB Agent", page_icon="📊")

# --- CUSTOM LOGO ---
# Upload your logo to GitHub first, then reference it here. 
# A transparent PNG with bright white or cyan text is best for the dark theme.
st.image(".streamlit/db_agent_logo.png", width=350) # Adjust the width as needed!

st.title("Talk or Type to your Database 🎙️⌨️📊")
st.write("Click the microphone to speak, or type your question in the chat box below.")

# --- SIDEBAR & SETTINGS ---
with st.sidebar:
    st.header("⚙️ Settings")
    if st.button("🗑️ Clear Chat History"):
        # This empties the app's memory
        st.session_state.messages = []
        # This refreshes the screen immediately
        st.rerun()

# 1. Initialize the app's memory
if "messages" not in st.session_state:
    st.session_state.messages = []

# 2. Draw all previous messages (Text and Audio) to the screen
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if "text" in message:
            st.write(message["text"])
        if "audio" in message:
            st.audio(message["audio"], format="audio/wav" if message["role"] == "user" else "audio/mpeg")

# --- HELPER FUNCTION: Handle the response from n8n ---
def process_n8n_response(response):
    if response.status_code == 200:
        response_data = response.json()
        
        # If n8n wrapped the data in a list [ ], grab the dictionary inside
        if isinstance(response_data, list) and len(response_data) > 0:
            response_data = response_data[0]
            
        if "text" in response_data and "audio_b64" in response_data:
            if response_data["audio_b64"] == "filesystem-v2":
                st.error("Audio error: n8n sent a filesystem link instead of actual data.")
            else:
                ai_text = response_data["text"]
                ai_audio_bytes = base64.b64decode(response_data["audio_b64"])
                
                with st.chat_message("assistant"):
                    st.write(ai_text)
                    st.audio(ai_audio_bytes, format="audio/mpeg")
                    
                st.session_state.messages.append({"role": "assistant", "text": ai_text, "audio": ai_audio_bytes})
                st.rerun() # Refresh the page to reset the inputs
        else:
            st.error(f"Unexpected format from n8n. Raw data: {response_data}")
    else:
        st.error(f"Error from n8n: {response.status_code}")

# --- INPUT WIDGETS ---
# The dynamic microphone widget
current_mic_key = f"mic_{len(st.session_state.messages)}"
audio_bytes = audio_recorder("Record your question:", key=current_mic_key)

# The new text input widget
text_prompt = st.chat_input("Or type your question here...")

# Hostinger disguise
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# --- SCENARIO A: The User Spoke ---
if audio_bytes:
    with st.chat_message("user"):
        st.audio(audio_bytes, format="audio/wav")
    st.session_state.messages.append({"role": "user", "audio": audio_bytes})
    
    with st.spinner("Listening and querying the database..."):
        # Your original audio webhook
        n8n_audio_url = "https://n8n.srv862460.hstgr.cloud/webhook/4cf01dae-deb3-4fdf-aec4-78e3c072880e" 
        files = {"data": ("question.wav", audio_bytes, "audio/wav")}
        
        try:
            response = requests.post(n8n_audio_url, files=files, headers=headers, timeout=30)
            process_n8n_response(response)
        except Exception as e:
            st.error(f"Failed to connect to n8n: {e}")

# --- SCENARIO B: The User Typed ---
elif text_prompt:
    with st.chat_message("user"):
        st.write(text_prompt)
    st.session_state.messages.append({"role": "user", "text": text_prompt})
    
    with st.spinner("Reading and querying the database..."):
        # ⚠️ PASTE YOUR BRAND NEW TEXT WEBHOOK URL HERE
        n8n_text_url = "https://n8n.srv862460.hstgr.cloud/webhook/ca0702e5-e555-43a8-83b1-9e7f059e90d9" 
        
        # We send the text as a JSON payload, exactly how the AI Agent expects it!
        payload = {"text": text_prompt}
        
        try:
            response = requests.post(n8n_text_url, json=payload, headers=headers, timeout=30)
            process_n8n_response(response)
        except Exception as e:
            st.error(f"Failed to connect to n8n: {e}")
