```
streamlit run app.py
```

## ✨ Funzionalità

### 💬 Tab Chat
- **Conversazione interattiva** con l'agent
- **Visualizzazione messaggi** user/assistant
- **Esempi veloci** (pulsanti preimpostati)
- **Input testuale** con invio

### 🔍 Tab Debug & Trace
- **Traccia completa** di ogni conversazione
- **Visualizzazione step-by-step**:
  - 🔧 Tool calls (con parametri JSON)
  - 📦 Tool responses (espandibili)
  - 🤖 Reasoning dell'assistant
- **Statistiche** (tool calls, conversazioni, steps medi)
- **Esportazione log** in JSON

### ⚙️ Sidebar
- **Selezione provider** (Groq/Anthropic/OpenAI)
- **Selezione modello** dinamica
- **Stato agent** (attivo/inattivo)
- **Metriche live** (messaggi, tracce)
- **Pulsanti utility** (pulisci, esporta)
- **Lista tools** disponibili

## 🎨 Design Features

- ✅ **Responsive** (layout wide)
- ✅ **CSS personalizzato** (colori per tipo messaggio)
- ✅ **Expander** per tool calls/responses
- ✅ **Logging** automatico su file
- ✅ **Error handling** completo
- ✅ **Async/await** per performance

## 📁 Struttura File
```
project/
├── app.py              # Frontend Streamlit (questo file)
├── server.py           # MCP Server (artifact precedente)
├── requirements.txt
├── .env
└── agent_debug.log     # Log automatico