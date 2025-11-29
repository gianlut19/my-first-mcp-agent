#!/usr/bin/env python3
"""
MCP Server per WeatherAPI.com
Implementa 5 endpoint principali: Current, Forecast, History, Search, Astronomy
"""

import os
import sys

# CRITICO: Disabilita COMPLETAMENTE stdout PRIMA di qualsiasi import
# Questo evita che dotenv o altri moduli loggino su stdout
_original_stdout = sys.stdout
sys.stdout = open(os.devnull, 'w')

# Ora carica dotenv senza output
from dotenv import load_dotenv
load_dotenv()

# Ripristina stdout solo per MCP (che usa stdio in modo controllato)
sys.stdout = _original_stdout

import asyncio
import json
from datetime import datetime
from typing import Any
from urllib.parse import urlencode

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Configurazione
API_KEY = os.getenv("WEATHERAPI_KEY", "")
BASE_URL = "http://api.weatherapi.com/v1"

server = Server("weatherapi-server")


def build_url(endpoint: str, params: dict[str, Any]) -> str:
    """Costruisce l'URL completo per la richiesta API"""
    params["key"] = API_KEY
    query_string = urlencode({k: v for k, v in params.items() if v is not None})
    return f"{BASE_URL}/{endpoint}.json?{query_string}"


async def make_request(url: str) -> dict[str, Any]:
    """Effettua la richiesta HTTP e gestisce errori"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Elenca tutti gli strumenti disponibili"""
    return [
        Tool(
            name="get_current_weather",
            description="Ottiene le condizioni meteo attuali per una località. "
            "Supporta città, coordinate lat/lon, codici postali, IP.",
            inputSchema={
                "type": "object",
                "properties": {
                    "q": {
                        "type": "string",
                        "description": "Località: nome città (es: London), "
                        "lat,lon (es: 48.8567,2.3508), "
                        "codice postale (es: 10001), IP address",
                    },
                    "aqi": {
                        "type": "string",
                        "enum": ["yes", "no"],
                        "description": "Includi dati qualità dell'aria",
                        "default": "no",
                    },
                    "lang": {
                        "type": "string",
                        "description": "Codice lingua (es: it, en, fr, de)",
                        "default": "en",
                    },
                },
                "required": ["q"],
            },
        ),
        Tool(
            name="get_forecast",
            description="Ottiene previsioni meteo fino a 14 giorni. "
            "Include dati orari, astronomia, allerte meteo.",
            inputSchema={
                "type": "object",
                "properties": {
                    "q": {
                        "type": "string",
                        "description": "Località (città, lat,lon, codice postale)",
                    },
                    "days": {
                        "type": ["integer", "string"],
                        "description": "Numero di giorni di previsione (1-14)",
                        "minimum": 1,
                        "maximum": 14,
                        "default": 3,
                    },
                    "aqi": {
                        "type": "string",
                        "enum": ["yes", "no"],
                        "description": "Includi qualità dell'aria",
                        "default": "no",
                    },
                    "alerts": {
                        "type": "string",
                        "enum": ["yes", "no"],
                        "description": "Includi allerte meteo",
                        "default": "yes",
                    },
                    "lang": {
                        "type": "string",
                        "description": "Codice lingua",
                        "default": "en",
                    },
                },
                "required": ["q"],
            },
        ),
        Tool(
            name="get_history",
            description="Ottiene dati meteo storici dal 1 gennaio 2010. "
            "Include temperatura, precipitazioni, vento per data specifica.",
            inputSchema={
                "type": "object",
                "properties": {
                    "q": {
                        "type": "string",
                        "description": "Località (città, lat,lon, codice postale)",
                    },
                    "dt": {
                        "type": "string",
                        "description": "Data in formato yyyy-MM-dd (es: 2023-01-15)",
                    },
                    "end_dt": {
                        "type": "string",
                        "description": "Data finale per range (opzionale, max 30 giorni)",
                    },
                    "lang": {
                        "type": "string",
                        "description": "Codice lingua",
                        "default": "en",
                    },
                },
                "required": ["q", "dt"],
            },
        ),
        Tool(
            name="search_location",
            description="Cerca località per nome. Utile per autocomplete "
            "e trovare coordinate esatte prima di altre chiamate.",
            inputSchema={
                "type": "object",
                "properties": {
                    "q": {
                        "type": "string",
                        "description": "Termine di ricerca (es: 'Lond' per trovare Londra)",
                    }
                },
                "required": ["q"],
            },
        ),
        Tool(
            name="get_astronomy",
            description="Ottiene dati astronomici: alba, tramonto, "
            "fasi lunari, levata/tramonto luna per una data specifica.",
            inputSchema={
                "type": "object",
                "properties": {
                    "q": {
                        "type": "string",
                        "description": "Località (città, lat,lon, codice postale)",
                    },
                    "dt": {
                        "type": "string",
                        "description": "Data in formato yyyy-MM-dd (opzionale, default oggi)",
                    },
                },
                "required": ["q"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Gestisce le chiamate agli strumenti"""
    
    if not API_KEY:
        return [
            TextContent(
                type="text",
                text="Errore: WEATHERAPI_KEY non configurata. "
                "Imposta la variabile d'ambiente con la tua API key.",
            )
        ]

    try:
        if name == "get_current_weather":
            url = build_url(
                "current",
                {
                    "q": arguments["q"],
                    "aqi": arguments.get("aqi", "no"),
                    "lang": arguments.get("lang", "en"),
                },
            )
            data = await make_request(url)
            
            location = data["location"]
            current = data["current"]
            
            result = f"""**Meteo Attuale - {location['name']}, {location['country']}**
Ora locale: {location['localtime']}

🌡️ Temperatura: {current['temp_c']}°C ({current['temp_f']}°F)
🤚 Percepita: {current['feelslike_c']}°C
☁️ Condizioni: {current['condition']['text']}
💧 Umidità: {current['humidity']}%
🌬️ Vento: {current['wind_kph']} km/h {current['wind_dir']}
🌧️ Precipitazioni: {current['precip_mm']} mm
👁️ Visibilità: {current['vis_km']} km
☀️ UV Index: {current['uv']}
"""
            
            if arguments.get("aqi") == "yes" and "air_quality" in current:
                aqi = current["air_quality"]
                result += f"\n**Qualità dell'Aria**\nUS EPA Index: {aqi.get('us-epa-index', 'N/A')}\n"
            
            return [TextContent(type="text", text=result)]

        elif name == "get_forecast":
            # Converti days in intero se è una stringa
            days = arguments.get("days", 3)
            if isinstance(days, str):
                days = int(days)
            
            url = build_url(
                "forecast",
                {
                    "q": arguments["q"],
                    "days": days,
                    "aqi": arguments.get("aqi", "no"),
                    "alerts": arguments.get("alerts", "yes"),
                    "lang": arguments.get("lang", "en"),
                },
            )
            data = await make_request(url)
            
            location = data["location"]
            forecast = data["forecast"]["forecastday"]
            
            result = f"**Previsioni Meteo - {location['name']}, {location['country']}**\n\n"
            
            for day in forecast:
                d = day["day"]
                result += f"""📅 {day['date']}
🌡️ Min/Max: {d['mintemp_c']}°C / {d['maxtemp_c']}°C
☁️ {d['condition']['text']}
🌧️ Precipitazioni: {d['totalprecip_mm']} mm
💨 Vento max: {d['maxwind_kph']} km/h
💧 Umidità media: {d['avghumidity']}%
☀️ UV Index: {d['uv']}

"""
            
            if "alerts" in data and data["alerts"].get("alert"):
                result += "⚠️ **ALLERTE METEO**\n"
                for alert in data["alerts"]["alert"]:
                    result += f"- {alert['event']}: {alert['headline']}\n"
            
            return [TextContent(type="text", text=result)]

        elif name == "get_history":
            url = build_url(
                "history",
                {
                    "q": arguments["q"],
                    "dt": arguments["dt"],
                    "end_dt": arguments.get("end_dt"),
                    "lang": arguments.get("lang", "en"),
                },
            )
            data = await make_request(url)
            
            location = data["location"]
            forecast = data["forecast"]["forecastday"]
            
            result = f"**Dati Storici - {location['name']}, {location['country']}**\n\n"
            
            for day in forecast:
                d = day["day"]
                result += f"""📅 {day['date']}
🌡️ Min/Max/Media: {d['mintemp_c']}°C / {d['maxtemp_c']}°C / {d['avgtemp_c']}°C
☁️ {d['condition']['text']}
🌧️ Precipitazioni totali: {d['totalprecip_mm']} mm
💨 Vento max: {d['maxwind_kph']} km/h
💧 Umidità media: {d['avghumidity']}%
👁️ Visibilità media: {d['avgvis_km']} km

"""
            
            return [TextContent(type="text", text=result)]

        elif name == "search_location":
            url = build_url("search", {"q": arguments["q"]})
            data = await make_request(url)
            
            if not data:
                return [TextContent(type="text", text="Nessuna località trovata.")]
            
            result = "**Località trovate:**\n\n"
            for loc in data:
                result += f"""📍 {loc['name']}, {loc['region']}, {loc['country']}
   Coordinate: {loc['lat']}, {loc['lon']}
   ID: {loc['id']}

"""
            
            return [TextContent(type="text", text=result)]

        elif name == "get_astronomy":
            url = build_url(
                "astronomy",
                {
                    "q": arguments["q"],
                    "dt": arguments.get("dt"),
                },
            )
            data = await make_request(url)
            
            location = data["location"]
            astro = data["astronomy"]["astro"]
            
            result = f"""**Dati Astronomici - {location['name']}, {location['country']}**
Data: {data['location']['localtime'].split()[0]}

🌅 Alba: {astro['sunrise']}
🌇 Tramonto: {astro['sunset']}
🌙 Levata luna: {astro['moonrise']}
🌑 Tramonto luna: {astro['moonset']}
🌓 Fase lunare: {astro['moon_phase']}
🌕 Illuminazione: {astro['moon_illumination']}%

☀️ Sole visibile: {'Sì' if astro['is_sun_up'] == 1 else 'No'}
🌙 Luna visibile: {'Sì' if astro['is_moon_up'] == 1 else 'No'}
"""
            
            return [TextContent(type="text", text=result)]

        else:
            return [TextContent(type="text", text=f"Strumento sconosciuto: {name}")]

    except httpx.HTTPStatusError as e:
        error_msg = f"Errore HTTP {e.response.status_code}"
        try:
            error_data = e.response.json()
            if "error" in error_data:
                error_msg += f": {error_data['error'].get('message', 'Errore sconosciuto')}"
        except:
            pass
        return [TextContent(type="text", text=error_msg)]
    
    except Exception as e:
        return [TextContent(type="text", text=f"Errore: {str(e)}")]


async def main():
    """Avvia il server MCP"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())