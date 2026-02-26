import streamlit as st
from audio_recorder_streamlit import audio_recorder
import requests
import base64

st.title("Talk to your Database 🎙️📊")
st.write("Click the microphone, ask a question, and wait for the database to reply.")

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

# 3. The Microphone Widget
audio_bytes = audio_recorder("Record your question:")

if audio_bytes:
    # Save and show the user's audio
    with st.chat_message("user"):
        st.audio(audio_bytes, format="audio/wav")
    st.session_state.messages.append({"role": "user", "audio": audio_bytes})
    
    with st.spinner("Querying the database..."):
        n8n_webhook_url = "https://n8n.srv862460.hstgr.cloud/webhook/4cf01dae-deb3-4fdf-aec4-78e3c072880e" 
        files = {"data": ("question.wav", audio_bytes, "audio/wav")}
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            
            response = requests.post(n8n_webhook_url, files=files, headers=headers, timeout=30)
            
            if response.status_code == 200:
                # Unpack the JSON response from n8n
                response_data = response.json()
                ai_text = response_data["text"]
                ai_audio_bytes = base64.b64decode(response_data["audio_b64"])
                
                # Show the text AND the audio in the chat bubble
                with st.chat_message("assistant"):
                    st.write(ai_text)
                    st.audio(ai_audio_bytes, format="audio/mpeg")
                    
                # Save both to memory
                st.session_state.messages.append({"role": "assistant", "text": ai_text, "audio": ai_audio_bytes})
                
            else:
                st.error(f"Error from n8n: {response.status_code}")
                
        except Exception as e:
            st.error(f"Failed to connect to n8n: {e}")
