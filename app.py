# app.py — Voice recorder/uploader
import io, uuid
from datetime import datetime, timezone

import streamlit as st
from audiorecorder import audiorecorder
import speech_recognition as sr
from supabase import create_client, Client

st.set_page_config(page_title="Voice Feedback", page_icon="🎤", layout="centered")
st.title("🎤 Voice Feedback")
st.caption("Record a short voice note; we’ll save the audio + transcript in Supabase.")

# --- Secrets (set these in Streamlit Cloud or local .streamlit/secrets.toml) ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
BUCKET = st.secrets.get("SUPABASE_BUCKET", "voice-recordings")
TABLE = st.secrets.get("SUPABASE_TABLE", "feedback")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---- Basic context fields (customize as you like) ----
col1, col2 = st.columns(2)
feedback_type = col1.selectbox("Feedback type", ["thermal", "visual", "acoustic", "IAQ", "other"])
room = col2.text_input("Room / Zone ID", placeholder="e.g., ARC_1119")
user_id = st.text_input("User ID (optional)", placeholder="netid or anonymous")

st.subheader("Record")
audio = audiorecorder("🎙️ Start recording", "🛑 Stop")

if len(audio) > 0:
    # Convert to wav bytes
    wav_bytes = io.BytesIO()
    audio.export(wav_bytes, format="wav")
    wav_bytes.seek(0)

    st.audio(wav_bytes, format="audio/wav")
    st.info(f"Duration: ~{round(len(audio) / 1000, 1)} sec")

    # Transcribe (Google Web Speech via SpeechRecognition)
    st.write("Transcribing…")
    wav_bytes.seek(0)
    r = sr.Recognizer()
    with sr.AudioFile(wav_bytes) as source:
        audio_data = r.record(source)

    transcript = ""
    try:
        transcript = r.recognize_google(audio_data)
        st.success("Transcript ready.")
        st.write("📝", transcript)
    except sr.UnknownValueError:
        st.warning("Could not understand the audio (no transcript).")
    except sr.RequestError as e:
        st.error(f"Google STT error: {e}")

    # Prepare filename + upload
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    fname = f"voice/{ts}_{uuid.uuid4().hex}.wav"
 # Prepare filename + upload
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    fname = f"voice/{ts}_{uuid.uuid4().hex}.wav"

    if st.button("💾 Save voice feedback"):
        try:
            # 1) Upload file to Storage
            wav_bytes.seek(0)
            supabase.storage.from_(BUCKET).upload(
                path=fname,
                file=wav_bytes.getvalue(),
                file_options={"content-type": "audio/wav", "x-upsert": "true"},
            )

            # 2) Insert DB row
            row = {
                "id": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "feedback_type": feedback_type,
                "feedback_text": transcript or None,
                "room": room or None,
                "user_id": user_id or None,
                "audio_path": fname,
                "audio_mime": "audio/wav",
                "source": "streamlit-app",
            }
            supabase.table(TABLE).insert(row).execute()

            st.success("Saved! Open the Playback page to listen.")
        except Exception as e:
            st.error(f"Save failed: {e}")
