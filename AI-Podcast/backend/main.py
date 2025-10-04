from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from agents import build_agent
from orchestrator import ConversationManager
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Podcast Generator API")

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "AI Podcast Generator API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.websocket("/ws/conversation")
async def conversation_ws(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    try:
        # Receive configuration
        config = await websocket.receive_json()
        logger.info(f"Received config: {config}")
        
        topic = config.get("topic", "AI and Technology")
        personaA = config.get("personaA")
        personaB = config.get("personaB")
        max_turns = config.get("max_turns", 6)
        voice_a = config.get("voice_a")  # Optional: custom voice ID
        voice_b = config.get("voice_b")  # Optional: custom voice ID
        
        # Build agents with optional custom personas
        logger.info("Building agents...")
        agent_a = build_agent(persona_prompt=personaA, role="host")
        agent_b = build_agent(persona_prompt=personaB, role="guest")
        
        # Create conversation manager with voices
        convo = ConversationManager(
            agent_a=agent_a,
            agent_b=agent_b,
            voice_a=voice_a,
            voice_b=voice_b,
            max_turns=max_turns
        )
        
        logger.info(f"Starting conversation about: {topic}")
        
        # Run conversation and stream turns
        async for turn in convo.run(topic):
            await websocket.send_json(turn)
            logger.info(f"Sent turn {turn['turn']} - {turn['role']}")
        
        logger.info("Conversation completed successfully")
        
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Error in conversation: {str(e)}", exc_info=True)
        try:
            await websocket.send_json({
                "error": str(e),
                "type": "error"
            })
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass
        logger.info("WebSocket connection closed")