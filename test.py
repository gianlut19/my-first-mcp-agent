import os
from dotenv import load_dotenv
import asyncio

load_dotenv()
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "")

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_groq import ChatGroq
from langchain.agents import create_agent

client = MultiServerMCPClient(
    {
        "weather": {
            "transport": "stdio",
            "command": "python",
            "args": ["server.py"],
        }
    }
)


async def main():
    tools = await client.get_tools()
    
    # Usa ChatGroq direttamente invece di "groq:model"
    llm = ChatGroq(
        model="openai/gpt-oss-120b",
        temperature=0,
        # Forza il formato OpenAI standard per tool calling
        model_kwargs={
            "tool_choice": "auto",
        }
    )
    
    agent = create_agent(llm, tools)
    
    response = await agent.ainvoke(
        {
            "messages": [
                {"role": "user", "content": "Mi puoi suggerire dove andare a camminare domani a Milano in base al meteo?"},
            ]
        }
    )
    
    messages_response = response["messages"]
    for msg in messages_response:
        print(f"\n{type(msg).__name__}:")
        print(msg.content)
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            print(f"Tool calls: {msg.tool_calls}")


if __name__ == "__main__":
    asyncio.run(main())