"""
Chainlit Weather Agent con streaming asincrono e visualizzazione tool calls
"""

import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from loguru import logger

import chainlit as cl
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

load_dotenv()

# Configurazione logger
logger.add("agent_debug.log", rotation="1 MB")

# Configurazione globale
PROVIDER_MODELS = {
    "OpenAI": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
    "Anthropic": ["claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"],
    "Groq": [
        "openai/gpt-oss-120b",
        "llama-3.3-70b-versatile", 
        "llama-3.1-70b-versatile", 
        "mixtral-8x7b-32768"
    ]
}


async def initialize_mcp_client():
    """Inizializza i client MCP (Weather + Travel)"""
    env = os.environ.copy()
    env["WEATHERAPI_KEY"] = os.getenv("WEATHERAPI_KEY", "")
    
    client = MultiServerMCPClient(
        {
            "weather": {
                "transport": "stdio",
                "command": "python",
                "args": ["server.py"],
                "env": env,
            },
            "travel": {
                "transport": "stdio",
                "command": "python",
                "args": ["travel_server.py"],
                "env": env,
            }
        }
    )
    
    tools = await client.get_tools()
    return client, tools


def get_llm(provider: str, model: str):
    """Ottiene il modello LLM in base al provider"""
    if provider == "OpenAI":
        return ChatOpenAI(
            model=model,
            temperature=0,
            streaming=True,
            api_key=os.getenv("OPENAI_API_KEY")
        )
    elif provider == "Anthropic":
        return ChatAnthropic(
            model=model,
            temperature=0,
            streaming=True,
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
    elif provider == "Groq":
        return ChatGroq(
            model=model,
            temperature=0,
            streaming=True,
            api_key=os.getenv("GROQ_API_KEY")
        )


@cl.on_chat_start
async def start():
    """Inizializza la sessione chat"""
    
    # Messaggio di benvenuto
    await cl.Message(
        content="# 🌤️ Weather Agent\n\nBenvenuto! Sto inizializzando l'agent...",
        author="System"
    ).send()
    
    # Configurazione provider
    settings = await cl.ChatSettings(
        [
            cl.input_widget.Select(
                id="provider",
                label="Provider LLM",
                values=list(PROVIDER_MODELS.keys()),
                initial_value="Groq",
            ),
            cl.input_widget.Select(
                id="model",
                label="Modello",
                values=PROVIDER_MODELS["Groq"],
                initial_value="openai/gpt-oss-120b",
            ),
        ]
    ).send()
    
    # Inizializza MCP client
    try:
        logger.info("Inizializzazione MCP client...")
        client, tools = await initialize_mcp_client()
        logger.info(f"MCP client inizializzato con {len(tools)} tools")
        
        # Ottieni LLM
        provider = settings.get("provider", "Groq")
        model = settings.get("model", "openai/gpt-oss-120b")
        logger.info(f"Inizializzazione LLM: {provider} - {model}")
        llm = get_llm(provider, model)
        
        # Crea agent
        logger.info("Creazione agent...")
        agent = create_react_agent(llm, tools)
        
        # Salva in sessione
        cl.user_session.set("agent", agent)
        cl.user_session.set("mcp_client", client)
        cl.user_session.set("provider", provider)
        cl.user_session.set("model", model)
        cl.user_session.set("conversation_history", [])
        
        # Messaggio di conferma
        await cl.Message(
            content=f"✅ **Agent inizializzato!**\n\n"
                   f"📡 Provider: `{provider}`\n"
                   f"🤖 Modello: `{model}`\n"
                   f"🔧 Tools disponibili: {len(tools)}\n\n"
                   f"Chiedimi informazioni sul meteo!",
            author="System"
        ).send()
        
        logger.info(f"Agent inizializzato: {provider} - {model}")
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Errore inizializzazione: {e}\n{error_details}")
        await cl.Message(
            content=f"❌ **Errore durante l'inizializzazione:**\n```\n{error_details}\n```",
            author="System"
        ).send()


@cl.on_settings_update
async def settings_update(settings):
    """Aggiorna le impostazioni quando l'utente le modifica"""
    provider = settings["provider"]
    model = settings["model"]
    
    # Aggiorna la lista dei modelli in base al provider
    if provider in PROVIDER_MODELS:
        # Ottieni nuovo LLM
        llm = get_llm(provider, model)
        
        # Ottieni tools dalla sessione
        client = cl.user_session.get("mcp_client")
        tools = await client.get_tools()
        
        # Ricrea agent
        agent = create_react_agent(llm, tools)
        
        # Aggiorna sessione
        cl.user_session.set("agent", agent)
        cl.user_session.set("provider", provider)
        cl.user_session.set("model", model)
        
        await cl.Message(
            content=f"✅ Configurazione aggiornata: {provider} - {model}",
            author="System"
        ).send()


async def stream_tool_call(tool_name: str, tool_args: dict, msg: cl.Message):
    """Mostra la chiamata al tool in modo animato"""
    # Header
    await msg.stream_token(f"\n\n🔧 **Chiamata tool: `{tool_name}`**\n\n")
    
    # Argomenti
    await msg.stream_token("```json\n")
    import json
    args_json = json.dumps(tool_args, indent=2, ensure_ascii=False)
    
    # Simula typing degli argomenti
    for char in args_json:
        await msg.stream_token(char)
        await asyncio.sleep(0.005)  # Velocità typing
    
    await msg.stream_token("\n```\n\n")


async def stream_tool_response(tool_name: str, response: str, msg: cl.Message):
    """Mostra la risposta del tool in modo collassabile"""
    await msg.stream_token(f"📦 **Risposta da `{tool_name}`:**\n\n")
    
    # Se la risposta è lunga, mostra solo l'inizio
    if len(response) > 200:
        preview = response[:200] + "..."
        await msg.stream_token(f"```\n{preview}\n```\n\n")
        
        # Aggiungi elemento collapsabile con la risposta completa
        elements = msg.elements or []
        elements.append(
            cl.Text(
                name=f"tool_response_{tool_name}",
                content=response,
                display="inline",
                language="text"
            )
        )
        msg.elements = elements
    else:
        # Risposta breve, mostrala direttamente
        for char in response:
            await msg.stream_token(char)
            await asyncio.sleep(0.01)
        await msg.stream_token("\n\n")


@cl.on_message
async def main(message: cl.Message):
    """Gestisce i messaggi dell'utente"""
    
    # Ottieni agent dalla sessione
    agent = cl.user_session.get("agent")
    
    if not agent:
        await cl.Message(
            content="❌ Agent non inizializzato. Ricarica la pagina.",
            author="System"
        ).send()
        return
    
    # Crea messaggio di risposta
    msg = cl.Message(content="", author="Assistant")
    
    # Crea step per mostrare il reasoning (collassato)
    async with cl.Step(name="🔍 Reasoning Chain", type="tool") as step:
        step.output = ""
        
        try:
            # Prepara la chiamata all'agent
            user_message = message.content
            
            # Variabili per tracciare lo stato
            tool_calls_made = []
            step_content = []
            
            # Step 1: Mostra "sta pensando"
            await cl.Message(
                content="",
                author="Assistant"
            ).send()
            
            # Aggiorna status
            async with cl.Step(name="💭 Sto analizzando la richiesta", type="run") as thinking_step:
                # Esegui l'agent in background e monitora
                response = await agent.ainvoke({
                    "messages": [{"role": "user", "content": user_message}]
                })
            
            # Analizza la risposta per estrarre tool calls e risultati
            final_response = ""
            
            for i, response_msg in enumerate(response["messages"]):
                msg_type = type(response_msg).__name__
                
                # Tool Call - Aggiungi allo step
                if msg_type == "AIMessage" and hasattr(response_msg, 'tool_calls') and response_msg.tool_calls:
                    for tool_call in response_msg.tool_calls:
                        tool_name = tool_call.get("name", "unknown")
                        tool_args = tool_call.get("args", {})
                        tool_calls_made.append(tool_name)
                        
                        # Aggiorna lo status live
                        async with cl.Step(name=f"🔧 Chiamata: {tool_name}", type="tool") as tool_step:
                            import json
                            tool_step.input = json.dumps(tool_args, indent=2, ensure_ascii=False)
                        
                        # Aggiungi allo step content
                        step_content.append(f"**Tool:** `{tool_name}`")
                        step_content.append(f"```json\n{json.dumps(tool_args, indent=2, ensure_ascii=False)}\n```")
                
                # Tool Response - Aggiungi allo step
                elif msg_type == "ToolMessage":
                    tool_name = getattr(response_msg, 'name', 'unknown')
                    tool_content = response_msg.content
                    
                    # Aggiorna status
                    async with cl.Step(name=f"📦 Risposta: {tool_name}", type="tool") as response_step:
                        response_step.output = tool_content[:500] + ("..." if len(tool_content) > 500 else "")
                    
                    # Aggiungi allo step content
                    step_content.append(f"**Risposta da {tool_name}:**")
                    step_content.append(f"```\n{tool_content}\n```")
                    step_content.append("---")
                
                # Risposta finale
                elif msg_type == "AIMessage" and response_msg.content:
                    final_response = response_msg.content
            
            # Popola lo step con tutta la catena
            step.output = "\n\n".join(step_content)
            
            # Ora invia SOLO la risposta finale con streaming
            final_msg = cl.Message(content="", author="Assistant")
            
            # Streaming della risposta finale
            for char in final_response:
                await final_msg.stream_token(char)
                await asyncio.sleep(0.01)
            
            await final_msg.send()
            
            # Salva nella cronologia
            conversation_history = cl.user_session.get("conversation_history", [])
            conversation_history.append({
                "timestamp": datetime.now().isoformat(),
                "user": user_message,
                "assistant": final_response,
                "tools_used": tool_calls_made
            })
            cl.user_session.set("conversation_history", conversation_history)
            
            logger.info(f"Risposta completata. Tools usati: {tool_calls_made}")
            
        except Exception as e:
            logger.error(f"Errore durante elaborazione messaggio: {e}")
            import traceback
            error_trace = traceback.format_exc()
            step.output = f"❌ Errore:\n```\n{error_trace}\n```"
            await cl.Message(
                content=f"❌ Si è verificato un errore durante l'elaborazione.",
                author="Assistant"
            ).send()


@cl.on_chat_end
async def end():
    """Pulisce le risorse quando la chat termina"""
    logger.info("Sessione chat terminata")
    
    # Chiudi il client MCP
    client = cl.user_session.get("mcp_client")
    if client:
        # Il client MCP si chiude automaticamente
        pass


# Configurazione opzionale per personalizzare l'interfaccia
@cl.set_starters
async def set_starters():
    return [
        cl.Starter(
            label="🗓️ Pianifica gita Milano",
            message="Pianifica una giornata a Milano domani, suggerisci attività in base al meteo",
            icon="/public/calendar.svg",
        ),
        cl.Starter(
            label="🌤️ Meteo + Attività Roma",
            message="Che tempo farà a Roma nei prossimi 3 giorni? Suggerisci cosa fare",
            icon="/public/sun.svg",
        ),
        cl.Starter(
            label="🍝 Meteo + Ristoranti Firenze",
            message="Meteo attuale a Firenze e suggerisci dove mangiare",
            icon="/public/food.svg",
        ),
        cl.Starter(
            label="📅 Itinerario Completo",
            message="Crea un itinerario completo per domani a Venezia basato sul meteo",
            icon="/public/map.svg",
        ),
    ]