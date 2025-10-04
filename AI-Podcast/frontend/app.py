import streamlit as st
import asyncio
import websockets
import json
import base64
from pathlib import Path
import time

st.set_page_config(
    page_title="AI Podcast Generator",
    page_icon="🎙️",
    layout="wide"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .podcast-turn {
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
        background-color: #f0f2f6;
    }
    .host-turn {
        background-color: #e3f2fd;
    }
    .guest-turn {
        background-color: #f3e5f5;
    }
    .audio-player {
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

st.title("🎙️ AI Podcast Generator with Voice")
st.markdown("Generate realistic podcast conversations with AI-powered voices")

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    max_turns = st.slider("Number of turns", min_value=2, max_value=12, value=6, step=2)
    
    st.markdown("---")
    st.markdown("### 🎤 Available Voices")
    st.markdown("""
    - **Rachel** (Female, warm)
    - **Adam** (Male, deep)
    - **Domi** (Female, confident)
    - **Antoni** (Male, friendly)
    
    Or use custom voice IDs from your ElevenLabs account.
    """)

# Main configuration
col1, col2 = st.columns(2)

with col1:
    st.subheader("🎤 Host Configuration")
    host_persona = st.text_area(
        "Host Persona",
        value="You are an engaging podcast host. Ask thoughtful questions, show curiosity, and keep the conversation flowing naturally. Keep questions concise (1-2 at a time).",
        height=150
    )
    host_voice = st.text_input("Host Voice ID (optional)", placeholder="21m00Tcm4TlvDq8ikWAM")

with col2:
    st.subheader("👤 Guest Configuration")
    guest_persona = st.text_area(
        "Guest Persona",
        value="You are a knowledgeable expert. Share insights clearly and conversationally. Provide examples when relevant but keep responses concise (3-5 sentences).",
        height=150
    )
    guest_voice = st.text_input("Guest Voice ID (optional)", placeholder="pNInz6obpgDQGcFmaJgB")

# Topic input
topic = st.text_input(
    "📝 Podcast Topic",
    value="The Future of Artificial Intelligence in Healthcare",
    placeholder="Enter the topic for your podcast..."
)

# Initialize session state
if "transcript" not in st.session_state:
    st.session_state.transcript = []
if "is_generating" not in st.session_state:
    st.session_state.is_generating = False

async def run_conversation():
    """Run the podcast conversation via WebSocket"""
    uri = "ws://localhost:8000/ws/conversation"
    
    try:
        async with websockets.connect(uri, ping_interval=30, ping_timeout=30) as ws:
            # Send configuration
            config = {
                "topic": topic,
                "personaA": host_persona or None,
                "personaB": guest_persona or None,
                "max_turns": max_turns,
                "voice_a": host_voice or None,
                "voice_b": guest_voice or None
            }
            
            await ws.send(json.dumps(config))
            
            # Receive and process messages
            async for msg in ws:
                data = json.loads(msg)
                
                if data.get("type") == "error":
                    st.error(f"Error: {data.get('error')}")
                    break
                
                yield data
                
    except Exception as e:
        st.error(f"Connection error: {str(e)}")
        st.info("Make sure FastAPI is running: `uvicorn main:app --reload`")

def display_turn(turn_data, index):
    """Display a single turn with text and audio"""
    role = turn_data.get("role", "Speaker")
    text = turn_data.get("text", "")
    audio_b64 = turn_data.get("audio")
    
    # Style based on role
    css_class = "host-turn" if role == "Host" else "guest-turn"
    
    with st.container():
        st.markdown(f'<div class="podcast-turn {css_class}">', unsafe_allow_html=True)
        st.markdown(f"**{role}** (Turn {index + 1})")
        st.write(text)
        
        # Audio player with debugging
        if audio_b64:
            try:
                audio_bytes = base64.b64decode(audio_b64)
                st.audio(audio_bytes, format="audio/mpeg")
                st.caption(f"🔊 Audio size: {len(audio_bytes)} bytes")
            except Exception as e:
                st.error(f"Could not load audio: {str(e)}")
                st.caption(f"Audio data length: {len(audio_b64) if audio_b64 else 0}")
        else:
            st.warning("⚠️ No audio generated for this turn")
        
        st.markdown('</div>', unsafe_allow_html=True)

# Control buttons
col_btn1, col_btn2, col_btn3 = st.columns([2, 2, 6])

with col_btn1:
    start_button = st.button("▶️ Start Podcast", disabled=st.session_state.is_generating, type="primary")

with col_btn2:
    clear_button = st.button("🗑️ Clear", disabled=st.session_state.is_generating)

if clear_button:
    st.session_state.transcript = []
    st.rerun()

# Main conversation area
st.markdown("---")

if start_button:
    st.session_state.transcript = []
    st.session_state.is_generating = True
    
    # Create placeholder for live updates
    status_placeholder = st.empty()
    transcript_placeholder = st.empty()
    
    async def generate_podcast():
        status_placeholder.info("🎙️ Generating podcast... This may take a moment.")
        
        try:
            async for turn in run_conversation():
                st.session_state.transcript.append(turn)
                
                # Update display
                with transcript_placeholder.container():
                    for idx, turn_data in enumerate(st.session_state.transcript):
                        display_turn(turn_data, idx)
            
            status_placeholder.success("✅ Podcast generated successfully!")
            time.sleep(2)
            status_placeholder.empty()
            
        except Exception as e:
            status_placeholder.error(f"Error: {str(e)}")
        finally:
            st.session_state.is_generating = False
    
    # Run async function
    asyncio.run(generate_podcast())
    st.rerun()

# Display existing transcript
if st.session_state.transcript:
    st.subheader("📝 Podcast Transcript")
    for idx, turn_data in enumerate(st.session_state.transcript):
        display_turn(turn_data, idx)
    
    # Download option
    st.markdown("---")
    transcript_text = "\n\n".join([
        f"{turn['role']}: {turn['text']}"
        for turn in st.session_state.transcript
    ])
    
    st.download_button(
        label="📥 Download Transcript",
        data=transcript_text,
        file_name=f"podcast_transcript_{int(time.time())}.txt",
        mime="text/plain"
    )