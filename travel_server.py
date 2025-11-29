#!/usr/bin/env python3
"""
MCP Server per Travel Planning
Suggerisce attività, ristoranti e itinerari basati su località e condizioni
"""

import os
import sys

# Disabilita stdout per MCP
_original_stdout = sys.stdout
sys.stdout = open(os.devnull, 'w')

from dotenv import load_dotenv
load_dotenv()

sys.stdout = _original_stdout

import asyncio
import json
from datetime import datetime
from typing import Any, List, Dict

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

server = Server("travel-planner-server")


# Database simulato di attività (in produzione useresti un vero DB o API)
ACTIVITIES_DB = {
    "indoor": [
        {
            "name": "Musei e Gallerie d'Arte",
            "description": "Visita musei, gallerie, mostre",
            "suitable_weather": ["rain", "cold", "snow"],
            "duration": "2-4 ore",
            "type": "cultura"
        },
        {
            "name": "Shopping Centers",
            "description": "Centri commerciali, boutique al coperto",
            "suitable_weather": ["rain", "cold", "hot"],
            "duration": "2-3 ore",
            "type": "shopping"
        },
        {
            "name": "Cinema o Teatro",
            "description": "Film, spettacoli teatrali, concerti al coperto",
            "suitable_weather": ["rain", "cold", "hot"],
            "duration": "2-3 ore",
            "type": "intrattenimento"
        },
        {
            "name": "Spa e Centri Benessere",
            "description": "Relax, massaggi, terme",
            "suitable_weather": ["rain", "cold"],
            "duration": "2-4 ore",
            "type": "relax"
        },
        {
            "name": "Ristoranti e Caffè Storici",
            "description": "Tour gastronomico al coperto",
            "suitable_weather": ["rain", "cold", "hot"],
            "duration": "1-2 ore",
            "type": "food"
        },
    ],
    "outdoor": [
        {
            "name": "Parchi e Giardini",
            "description": "Passeggiate, picnic, relax all'aperto",
            "suitable_weather": ["sunny", "mild", "partly_cloudy"],
            "duration": "1-3 ore",
            "type": "natura"
        },
        {
            "name": "Tour Architettonici a Piedi",
            "description": "Scopri monumenti e architettura",
            "suitable_weather": ["sunny", "mild", "partly_cloudy"],
            "duration": "2-4 ore",
            "type": "cultura"
        },
        {
            "name": "Mercati all'Aperto",
            "description": "Mercati locali, street food",
            "suitable_weather": ["sunny", "mild"],
            "duration": "1-2 ore",
            "type": "shopping"
        },
        {
            "name": "Attività Sportive",
            "description": "Ciclismo, jogging, sport",
            "suitable_weather": ["sunny", "mild"],
            "duration": "1-3 ore",
            "type": "sport"
        },
        {
            "name": "Aperitivi all'Aperto",
            "description": "Bar con terrazze, rooftop",
            "suitable_weather": ["sunny", "mild"],
            "duration": "1-2 ore",
            "type": "food"
        },
    ],
    "mixed": [
        {
            "name": "Tour Guidati della Città",
            "description": "Bus turistici, tour guidati misti",
            "suitable_weather": ["any"],
            "duration": "3-4 ore",
            "type": "cultura"
        },
        {
            "name": "Cooking Class",
            "description": "Corsi di cucina locale",
            "suitable_weather": ["any"],
            "duration": "2-3 ore",
            "type": "food"
        },
    ]
}

RESTAURANTS_DB = {
    "Milano": [
        {"name": "Trattoria Milanese", "type": "tradizionale", "price": "€€", "specialty": "Cucina milanese"},
        {"name": "Luini", "type": "street_food", "price": "€", "specialty": "Panzerotti"},
        {"name": "Eataly Smeraldo", "type": "food_hall", "price": "€€", "specialty": "Prodotti italiani"},
    ],
    "Roma": [
        {"name": "Roscioli", "type": "bistrot", "price": "€€€", "specialty": "Cucina romana"},
        {"name": "Trapizzino", "type": "street_food", "price": "€", "specialty": "Trapizzini"},
    ],
    "default": [
        {"name": "Ristorante Locale", "type": "tradizionale", "price": "€€", "specialty": "Cucina locale"},
    ]
}


def classify_weather(weather_condition: str, temp: float) -> str:
    """Classifica le condizioni meteo per suggerire attività"""
    condition_lower = weather_condition.lower()
    
    if "rain" in condition_lower or "pioggia" in condition_lower:
        return "rain"
    elif "snow" in condition_lower or "neve" in condition_lower:
        return "snow"
    elif "sunny" in condition_lower or "clear" in condition_lower or "sereno" in condition_lower:
        if temp > 28:
            return "hot"
        return "sunny"
    elif temp < 5:
        return "cold"
    elif temp < 18:
        return "mild"
    else:
        return "partly_cloudy"


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Elenca tutti gli strumenti disponibili"""
    return [
        Tool(
            name="suggest_activities",
            description="Suggerisce attività basate sulle condizioni meteo e preferenze. "
            "Usa questo tool DOPO aver ottenuto le previsioni meteo dal weather agent.",
            inputSchema={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "Località (es: Milano, Roma)",
                    },
                    "weather_condition": {
                        "type": "string",
                        "description": "Condizione meteo attuale/prevista (es: 'Sunny', 'Rainy', 'Partly cloudy')",
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Temperatura in gradi Celsius",
                    },
                    "preferences": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Preferenze utente: cultura, sport, food, shopping, relax, natura",
                        "default": [],
                    },
                    "duration": {
                        "type": "string",
                        "description": "Durata disponibile: short (1-2h), medium (2-4h), long (4-8h)",
                        "default": "medium",
                    },
                },
                "required": ["location", "weather_condition", "temperature"],
            },
        ),
        Tool(
            name="suggest_restaurants",
            description="Suggerisce ristoranti nella località specificata",
            inputSchema={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "Località (es: Milano)",
                    },
                    "meal_type": {
                        "type": "string",
                        "enum": ["breakfast", "lunch", "dinner", "aperitivo"],
                        "description": "Tipo di pasto",
                        "default": "lunch",
                    },
                    "cuisine_type": {
                        "type": "string",
                        "description": "Tipo di cucina preferita (tradizionale, street_food, fine_dining)",
                        "default": "tradizionale",
                    },
                    "budget": {
                        "type": "string",
                        "enum": ["€", "€€", "€€€"],
                        "description": "Budget",
                        "default": "€€",
                    },
                },
                "required": ["location"],
            },
        ),
        Tool(
            name="create_itinerary",
            description="Crea un itinerario completo per la giornata combinando attività e ristoranti. "
            "Usa DOPO aver ottenuto meteo, attività e ristoranti.",
            inputSchema={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "Località",
                    },
                    "activities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista di attività da includere",
                    },
                    "restaurants": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista di ristoranti da includere",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Ora di inizio (es: 09:00)",
                        "default": "09:00",
                    },
                },
                "required": ["location", "activities"],
            },
        ),
        Tool(
            name="get_travel_tips",
            description="Fornisce consigli di viaggio specifici per la località e il meteo",
            inputSchema={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "Località",
                    },
                    "weather_condition": {
                        "type": "string",
                        "description": "Condizione meteo",
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Temperatura in °C",
                    },
                },
                "required": ["location", "weather_condition", "temperature"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Gestisce le chiamate agli strumenti"""
    
    try:
        if name == "suggest_activities":
            location = arguments["location"]
            weather_condition = arguments["weather_condition"]
            temperature = arguments["temperature"]
            preferences = arguments.get("preferences", [])
            duration = arguments.get("duration", "medium")
            
            # Classifica il meteo
            weather_class = classify_weather(weather_condition, temperature)
            
            # Determina se preferire indoor o outdoor
            prefer_indoor = weather_class in ["rain", "snow", "cold", "hot"]
            
            # Filtra attività
            suitable_activities = []
            
            # Priorità: indoor se brutto tempo, outdoor se bello
            primary_category = "indoor" if prefer_indoor else "outdoor"
            secondary_category = "outdoor" if prefer_indoor else "indoor"
            
            for activity in ACTIVITIES_DB[primary_category]:
                if weather_class in activity["suitable_weather"] or "any" in activity["suitable_weather"]:
                    if not preferences or activity["type"] in preferences:
                        suitable_activities.append(activity)
            
            # Aggiungi attività mixed
            for activity in ACTIVITIES_DB["mixed"]:
                if not preferences or activity["type"] in preferences:
                    suitable_activities.append(activity)
            
            # Se poche attività, aggiungi dalla categoria secondaria
            if len(suitable_activities) < 3:
                for activity in ACTIVITIES_DB[secondary_category]:
                    if not preferences or activity["type"] in preferences:
                        suitable_activities.append(activity)
            
            # Limita in base alla durata
            if duration == "short":
                suitable_activities = [a for a in suitable_activities if "1-2" in a["duration"]]
            
            # Formatta risultato
            result = f"**Attività consigliate per {location}**\n\n"
            result += f"🌡️ Meteo: {weather_condition}, {temperature}°C\n"
            result += f"📊 Condizioni: {'Al coperto consigliato' if prefer_indoor else 'Perfetto per stare all\'aperto'}\n\n"
            
            for i, activity in enumerate(suitable_activities[:5], 1):
                result += f"{i}. **{activity['name']}**\n"
                result += f"   - {activity['description']}\n"
                result += f"   - Durata: {activity['duration']}\n"
                result += f"   - Tipo: {activity['type']}\n\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "suggest_restaurants":
            location = arguments["location"]
            meal_type = arguments.get("meal_type", "lunch")
            cuisine_type = arguments.get("cuisine_type", "tradizionale")
            budget = arguments.get("budget", "€€")
            
            # Ottieni ristoranti per località
            restaurants = RESTAURANTS_DB.get(location, RESTAURANTS_DB["default"])
            
            # Filtra per budget
            filtered = [r for r in restaurants if r["price"] == budget or budget == "€€"]
            
            result = f"**Ristoranti consigliati a {location}**\n\n"
            result += f"🍽️ Pasto: {meal_type}\n"
            result += f"💰 Budget: {budget}\n\n"
            
            for i, restaurant in enumerate(filtered[:3], 1):
                result += f"{i}. **{restaurant['name']}**\n"
                result += f"   - Tipo: {restaurant['type']}\n"
                result += f"   - Specialità: {restaurant['specialty']}\n"
                result += f"   - Prezzo: {restaurant['price']}\n\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "create_itinerary":
            location = arguments["location"]
            activities = arguments["activities"]
            restaurants = arguments.get("restaurants", [])
            start_time = arguments.get("start_time", "09:00")
            
            result = f"# 📅 Itinerario per {location}\n\n"
            result += f"**Inizio:** {start_time}\n\n"
            
            # Crea timeline
            times = ["09:00", "11:00", "13:00", "15:00", "17:00", "19:00"]
            timeline = []
            
            # Alterna attività e ristoranti
            for i, activity in enumerate(activities[:3]):
                timeline.append((times[i*2], activity, "activity"))
                if i < len(restaurants):
                    timeline.append((times[i*2+1], restaurants[i], "restaurant"))
            
            for time, item, type in timeline:
                icon = "🎯" if type == "activity" else "🍽️"
                result += f"**{time}** {icon} {item}\n\n"
            
            result += "\n💡 **Consigli:**\n"
            result += "- Porta sempre un ombrello pieghevole\n"
            result += "- Prenota i ristoranti in anticipo\n"
            result += "- Usa i mezzi pubblici o cammina\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "get_travel_tips":
            location = arguments["location"]
            weather_condition = arguments["weather_condition"]
            temperature = arguments["temperature"]
            
            weather_class = classify_weather(weather_condition, temperature)
            
            result = f"**Consigli di Viaggio per {location}**\n\n"
            
            # Abbigliamento
            result += "👕 **Abbigliamento:**\n"
            if weather_class == "rain":
                result += "- Giacca impermeabile, ombrello, scarpe chiuse\n"
            elif weather_class == "cold":
                result += "- Cappotto, sciarpa, guanti, cappello\n"
            elif weather_class == "hot":
                result += "- Abbigliamento leggero, cappello, crema solare\n"
            else:
                result += "- Vestiti a strati, giacca leggera\n"
            
            result += "\n🎒 **Cosa portare:**\n"
            result += "- Bottiglia d'acqua riutilizzabile\n"
            result += "- Power bank per smartphone\n"
            result += "- Mappa offline della città\n"
            
            result += "\n🚇 **Trasporti:**\n"
            result += "- Acquista biglietti giornalieri per risparmiare\n"
            result += "- App utili: Google Maps, Moovit\n"
            
            return [TextContent(type="text", text=result)]
        
        else:
            return [TextContent(type="text", text=f"Strumento sconosciuto: {name}")]
    
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