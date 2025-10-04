import os
import base64
import asyncio
from langchain_core.messages import HumanMessage, AIMessage
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv
import logging

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConversationManager:
    def __init__(self, agent_a, agent_b, voice_a=None, voice_b=None, max_turns=6):
        self.agent_a = agent_a
        self.agent_b = agent_b
        self.max_turns = max_turns
        
        # ElevenLabs setup
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            logger.error("ELEVENLABS_API_KEY not found in environment variables!")
            raise ValueError("ELEVENLABS_API_KEY is required")
        
        logger.info(f"Initializing ElevenLabs client with API key: {api_key[:8]}...")
        self.elevenlabs_client = ElevenLabs(api_key=api_key)
        
        # Voice IDs for each speaker (use default voices if not provided)
        self.voice_a = voice_a or "21m00Tcm4TlvDq8ikWAM"  # Rachel - Female
        self.voice_b = voice_b or "pNInz6obpgDQGcFmaJgB"  # Adam - Male
        
        logger.info(f"Using voices - Host: {self.voice_a}, Guest: {self.voice_b}")
        
        # Conversation history for context
        self.conversation_history = []

    async def generate_audio(self, text: str, voice_id: str) -> str:
        """Generate audio from text using ElevenLabs and return base64 encoded string"""
        try:
            logger.info(f"Generating audio for text (length: {len(text)}) with voice: {voice_id}")
            
            # Use synchronous generate (ElevenLabs doesn't have true async yet)
            # We'll run it in executor to avoid blocking
            loop = asyncio.get_event_loop()
            
            def _generate():
                try:
                    # Generate audio using the correct API method
                    audio_generator = self.elevenlabs_client.text_to_speech.convert(
                        voice_id=voice_id,
                        text=text,
                        model_id="eleven_multilingual_v2"
                    )
                    
                    # Collect all chunks
                    chunks = []
                    for chunk in audio_generator:
                        if chunk:
                            chunks.append(chunk)
                    
                    audio_bytes = b"".join(chunks)
                    logger.info(f"Audio generated successfully, size: {len(audio_bytes)} bytes")
                    return audio_bytes
                    
                except Exception as e:
                    logger.error(f"Error in _generate: {str(e)}", exc_info=True)
                    raise
            
            # Run in executor to avoid blocking
            audio_bytes = await loop.run_in_executor(None, _generate)
            
            if not audio_bytes:
                logger.error("Audio generation returned empty bytes")
                return None
            
            # Encode to base64 for JSON transmission
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
            logger.info(f"Audio encoded to base64, length: {len(audio_b64)}")
            return audio_b64
            
        except Exception as e:
            logger.error(f"Error generating audio: {str(e)}", exc_info=True)
            return None

    async def run(self, topic: str):
        """Run the podcast conversation"""
        
        logger.info(f"Starting podcast conversation about: {topic}")
        
        # Opening prompt with better context
        opening_prompt = (
            f"You are starting a podcast conversation about: {topic}. "
            f"Begin by introducing yourself briefly (1-2 sentences) and sharing your initial thoughts on the topic. "
            f"Keep it conversational and engaging."
        )
        
        current_agent = self.agent_a
        other_agent = self.agent_b
        current_voice = self.voice_a
        other_voice = self.voice_b
        current_name = "Host"
        
        input_msg = opening_prompt
        
        for turn_num in range(self.max_turns):
            logger.info(f"=== Turn {turn_num} - {current_name} ===")
            
            # Unique thread ID for each turn to maintain context
            config = {"configurable": {"thread_id": "podcast_conversation"}}
            
            # Build messages with conversation history for context
            messages = self.conversation_history + [HumanMessage(content=input_msg)]
            
            # Get agent response
            logger.info("Invoking agent...")
            result = await current_agent.ainvoke(
                {"messages": messages},
                config=config
            )
            
            # Extract the reply
            reply = result["messages"][-1].content
            logger.info(f"Agent response: {reply[:100]}...")
            
            # Add to conversation history
            self.conversation_history.append(HumanMessage(content=input_msg))
            self.conversation_history.append(AIMessage(content=reply))
            
            # Generate audio asynchronously
            logger.info("Generating audio...")
            audio_b64 = await self.generate_audio(reply, current_voice)
            
            if audio_b64:
                logger.info("✅ Audio generated successfully")
            else:
                logger.warning("⚠️ Audio generation failed, returning text only")
            
            # Yield the complete turn
            turn_data = {
                "role": current_name,
                "text": reply,
                "turn": turn_num,
                "audio": audio_b64,
                "voice_id": current_voice
            }
            
            logger.info(f"Yielding turn data (has_audio: {audio_b64 is not None})")
            yield turn_data
            
            # Prepare next turn with conversational context
            if turn_num < self.max_turns - 1:
                if current_name == "Host":
                    input_msg = (
                        f"The guest just said: '{reply}'. "
                        f"Respond naturally to continue the conversation. "
                        f"You can ask follow-up questions, share insights, or explore related aspects. "
                        f"Keep your response concise (2-3 sentences)."
                    )
                else:
                    input_msg = (
                        f"The host just said: '{reply}'. "
                        f"Provide a thoughtful response. Share your expertise but keep it engaging and conversational. "
                        f"Aim for 3-4 sentences."
                    )
            
            # Switch speakers
            current_agent, other_agent = other_agent, current_agent
            current_voice, other_voice = other_voice, current_voice
            current_name = "Guest" if current_name == "Host" else "Host"
        
        logger.info("Conversation completed")