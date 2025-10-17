# pages/01_Playback.py — browse & play saved recordings
import streamlit as st
from supabase import create_client, Client

st.set_page_config(page_title="Playback", page_icon="🎧", layout="wide")
st.title("🎧 Playback")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
BUCKET = st.secrets.get("SUPABASE_BUCKET", "voice-recordings")
TABLE = st.secrets.get("SUPABASE_TABLE", "feedback")
SIGNED_SECONDS = int(st.secrets.get("SIGNED_SECONDS", 3600))  # 1 hour

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Filters
col1, col2 = st.columns(2)
room_q = col1.text_input("Filter by room (optional)")
type_q = col2.selectbox("Filter by type", ["", "thermal", "visual", "acoustic", "IAQ", "other"])

q = supabase.table(TABLE).select("*").order("timestamp", desc=True)
if room_q:
    q = q.ilike("room", f"%{room_q}%")
if type_q:
    q = q.eq("feedback_type", type_q)

res = q.limit(50).execute()
rows = res.data or []

if not rows:
    st.info("No recordings yet.")
else:
    for r in rows:
        label = f"{r.get('timestamp','')} • {r.get('room','(room?)')} • {r.get('feedback_type','')}"
        with st.expander(label, expanded=False):
            st.write("📝", r.get("feedback_text") or "_(no transcript)_")

            storage_path = r.get("audio_path")
            if storage_path:
                try:
                    signed = supabase.storage.from_(BUCKET).create_signed_url(storage_path, SIGNED_SECONDS)
                    url = signed.get("signedURL") or signed.get("signedUrl")
                    if url:
                        st.audio(url)
                    else:
                        st.warning("Could not create a signed URL. Check bucket policy/key.")
                except Exception as e:
                    st.error(f"Signed URL error: {e}")

