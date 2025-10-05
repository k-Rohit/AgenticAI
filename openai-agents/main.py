import os
import asyncio
from dotenv import load_dotenv
from agents import Agent, Runner, trace, function_tool
from openai.types.responses import ResponseTextDeltaEvent
from typing import Dict
from utils import send_email
from sales_agents import (
     sales_agent1,
     sales_agent2,
     sales_agent3
)

load_dotenv(override=True)

async def main():
    result = Runner.run_streamed(sales_agent1, input="Write a cold sales email")
    async for event in result.stream_events():
        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
            print(event.data.delta, end="", flush=True)

# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())



