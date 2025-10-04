from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv
import os

load_dotenv()

# Enhanced persona prompts
DEFAULT_HOST_PERSONA = """You are an engaging podcast host with a curious and enthusiastic personality.

Your style:
- Ask thoughtful, open-ended questions that encourage deep discussion
- Show genuine interest and enthusiasm for the topic
- Keep questions concise and focused (1-2 questions at a time)
- Build on what the guest says to create natural conversation flow
- Use conversational language, not overly formal
- Occasionally share brief insights or reactions to keep the dialogue dynamic

Remember: You're having a conversation, not conducting an interview. Be natural and engaging."""

DEFAULT_GUEST_PERSONA = """You are a knowledgeable expert being interviewed on a podcast.

Your style:
- Provide insightful, well-reasoned answers that demonstrate expertise
- Keep responses conversational and accessible (avoid jargon when possible)
- Share concrete examples, anecdotes, or case studies when relevant
- Be thoughtful but not overly lengthy (3-5 sentences typically)
- Show enthusiasm for the topic
- Occasionally ask clarifying questions if needed
- Balance depth with accessibility

Remember: You're having a conversation, not giving a lecture. Be engaging and personable."""


def build_agent(persona_prompt: str = None, role: str = "host", temperature: float = 0.8):
    """
    Build a conversational agent for podcast generation.
    
    Args:
        persona_prompt: Custom persona prompt (optional)
        role: Either "host" or "guest" (used for default prompts)
        temperature: Controls randomness (0.7-0.9 recommended for natural conversation)
    
    Returns:
        Compiled LangGraph agent with memory
    """
    
    # Use default prompts if none provided
    if persona_prompt is None:
        persona_prompt = DEFAULT_HOST_PERSONA if role == "host" else DEFAULT_GUEST_PERSONA
    
    # Use GPT-4 for better quality conversations
    llm = ChatOpenAI(
        model="gpt-4o-mini",  # Use gpt-4o for even better quality
        streaming=True,
        temperature=temperature,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Create prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", persona_prompt),
        MessagesPlaceholder(variable_name="messages"),
    ])
    
    # Create chain
    chain = prompt | llm
    
    def call_model(state: MessagesState):
        """Process the conversation state and generate response"""
        response = chain.invoke(state)
        return {"messages": [response]}
    
    # Build the graph
    workflow = StateGraph(state_schema=MessagesState)
    workflow.add_node("agent", call_model)
    workflow.add_edge(START, "agent")
    workflow.add_edge("agent", END)
    
    # Add memory for conversation continuity
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    
    return app