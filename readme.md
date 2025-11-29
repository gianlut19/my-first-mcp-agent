# 🌤️ Weather & Travel Agent

This project implements a **Multi-Function Conversational Agent** for travel planning and weather information retrieval. It leverages the **MCP (Multi-Server Communication Protocol)** architecture to integrate various backend services (Weather and Travel) with an LLM (Large Language Model) using the LangGraph ReAct Agent.

The user interface is handled by **Chainlit**, which provides a real-time visualization of the agent's reasoning chain (Tool Calls).

-----

## 🚀 Architecture

The system consists of three main components, all running as separate processes and communicating via the MCP protocol:

1.  **`server.py` (Weather Server):** An MCP server that interfaces the agent with the **WeatherAPI.com** API to obtain current weather, forecasts, history, and astronomical data.
2.  **`travel_server.py` (Travel Planner Server):** An MCP server that provides logic and simulated data (activities, restaurants) to suggest activities, restaurants, and create itineraries based on location, weather, and preferences.
3.  **`app.py` (Main Agent - Chainlit):** The main Chainlit application that manages the user interface, initializes the two MCP servers as tools, and uses **LangGraph (ReAct Agent)** to orchestrate tool calls based on the user's request.

-----

## 🛠️ Prerequisites

  * **Python 3.9+**
  * An API key for **WeatherAPI.com**.
  * An API key for a supported LLM provider (e.g., OpenAI, Anthropic, Groq).

-----

## ⚙️ Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/gianlut19/my-first-mcp-agent
    cd my-first-mcp-agent
    ```

2.  **Create and activate a virtual environment:**

    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/macOS
    .\venv\Scripts\activate   # Windows
    ```

3.  **Install dependencies:**

    ```bash
    pip install chainlit langchain_mcp_adapters httpx python-dotenv langgraph "langchain_openai>=0.1.0" "langchain_anthropic>=0.1.0" "langchain_groq>=0.1.0"
    ```

4.  **Configure Environment Variables:**
    Create a **`.env`** file in the root directory of the project and add your API keys:

    ```env
    # Key for the weather server
    WEATHERAPI_KEY="YOUR_WEATHERAPI_KEY"

    # Keys for supported LLM providers in app.py
    OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
    ANTHROPIC_API_KEY="YOUR_ANTHROPIC_API_KEY"
    GROQ_API_KEY="YOUR_GROQ_API_KEY"
    ```

-----

## ▶️ Getting Started

Run the Chainlit application from the project root directory:

```bash
chainlit run app.py -w
```

Open your browser to the address shown in the terminal (usually `http://localhost:8000`).

-----

## 🔧 Available Tools

The LLM agent has access to the following tools (MCP endpoints) to respond to user requests:

### ⛈️ Weather Tools (`server.py`)

| Tool Name | Description |
| :--- | :--- |
| `get_current_weather` | Gets the current weather conditions for a location. |
| `get_forecast` | Gets weather forecasts for up to 14 days, including hourly data and weather alerts. |
| `get_history` | Retrieves historical weather data from January 1, 2010, for a specific date or range. |
| `search_location` | Searches for locations by name, useful for finding exact coordinates. |
| `get_astronomy` | Retrieves astronomical data (sunrise, sunset, moon phases). |

### ✈️ Travel Planning Tools (`travel_server.py`)

| Tool Name | Description |
| :--- | :--- |
| `suggest_activities` | Suggests activities based on location, weather conditions, and preferences (culture, sports, relaxation, etc.). |
| `suggest_restaurants` | Suggests restaurants in the specified location. |
| `create_itinerary` | Creates a complete itinerary for the day by combining activities and restaurants. |
| `get_travel_tips` | Provides specific travel tips for the location and weather (e.g., clothing advice). |

-----

## 💡 Example Queries

The agent can execute complex reasoning chains by combining the tools:

  * **Weather + Activity:** "What is the current weather in Milan and suggest indoor activities?"
    *(Flow: `get_current_weather` → `suggest_activities`)*
  * **Weather + Restaurant:** "What will the weather be like in Rome for the next 3 days? Also, suggest a medium-budget restaurant for dinner."
    *(Flow: `get_forecast` → `suggest_restaurants`)*
  * **Full Planning:** "Create a complete itinerary for tomorrow in Venice. I want cultural activities and a cheap place for lunch."
    *(Flow: `get_forecast` → `suggest_activities` → `suggest_restaurants` → `create_itinerary`)*

-----

## 💻 Code Notes

  * **Stdio Communication (CRITICAL):** The `server.py` and `travel_server.py` files include critical code to **completely disable standard output (`sys.stdout`)** before any imports (like `dotenv`) and then restore it only for controlled MCP communication. This ensures that only the correctly formatted messages from the MCP protocol are exchanged, preventing errors in the `stdio` pipeline.
  * **Agent Orchestration:** The agent in `app.py` is built using **LangGraph (ReAct)** to dynamically determine the sequence of tools to call in response to the user's input.
  * **Interactive UI:** The visualization of the reasoning chain (Tool Calls and Responses) is managed using Chainlit's `cl.Step`, offering full transparency into the LLM's decision-making process.