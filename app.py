import streamlit as st
from audio_recorder_streamlit import audio_recorder
import requests

st.title("Talk to your Database 🎙️📊")
st.write("Click the microphone, ask a question, and wait for the database to reply.")

# 1. The Microphone Widget
audio_bytes = audio_recorder("Record your question:")

if audio_bytes:
    # Play back what the user just said
    st.audio(audio_bytes, format="audio/wav")
    
    with st.spinner("Querying the database..."):
        # 2. This is your EXACT n8n Test URL from your screenshot
        n8n_webhook_url = "https://n8n.srv862460.hstgr.cloud/webhook/4cf01dae-deb3-4fdf-aec4-78e3c072880e" 
        
        # 3. Package the audio file. The key "data" matches your n8n Whisper node.
        files = {"data": ("question.wav", audio_bytes, "audio/wav")}
        
        try:
            # ⚠️ CRITICAL: This must be 'files=files' so it sends as an audio file, not plain text
            response = requests.post(n8n_webhook_url, files=files)
            
            if response.status_code == 200:
                st.success("Answer generated!")
                # 4. Play the audio response returned by n8n AI
                st.audio(response.content, format="audio/mpeg")
            else:
                st.error(f"Error from n8n: {response.status_code}")
                
        except Exception as e:
            st.error(f"Failed to connect to n8n: {e}")

