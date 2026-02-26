import streamlit as st
from audio_recorder_streamlit import audio_recorder
import requests

st.title("Talk to your Database 🎙️📊")
st.write("Click the microphone, ask a question, and wait for the database to reply.")

# 1. Initialize the app's memory (Session State)
if "messages" not in st.session_state:
    st.session_state.messages = []

# 2. Draw all previous messages to the screen
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.audio(message["content"])

# 3. The Microphone Widget
audio_bytes = audio_recorder("Record your question:")

if audio_bytes:
    # Immediately show the user's new audio in a chat bubble and save it to memory
    with st.chat_message("user"):
        st.audio(audio_bytes, format="audio/wav")
    st.session_state.messages.append({"role": "user", "content": audio_bytes})
    
    with st.spinner("Querying the database..."):
        # Your live production Webhook
        n8n_webhook_url = "https://n8n.srv862460.hstgr.cloud/webhook/4cf01dae-deb3-4fdf-aec4-78e3c072880e" 
        
        files = {"data": ("question.wav", audio_bytes, "audio/wav")}
        
        try:
            # The browser disguise to bypass Hostinger's firewall
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            
            response = requests.post(n8n_webhook_url, files=files, headers=headers, timeout=30)
            
            if response.status_code == 200:
                # Show the AI's response in a chat bubble and save it to memory
                with st.chat_message("assistant"):
                    st.audio(response.content, format="audio/mpeg")
                st.session_state.messages.append({"role": "assistant", "content": response.content})
            else:
                st.error(f"Error from n8n: {response.status_code}")
                
        except Exception as e:
            st.error(f"Failed to connect to n8n: {e}")
