import httpx
import json
import logging
from typing import Dict, Any
from app.core.config import settings

logger = logging.getLogger("lingosphere.llm")

async def call_llm(system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
    """
    Sends request to configured LLM provider (Gemini or OpenAI).
    If no API key is provided, returns simulated agent responses.
    """
    # 1. Try Gemini API
    if settings.GEMINI_API_KEY:
        try:
            url = f"https://generativelens.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
            headers = {"Content-Type": "application/json"}
            
            # Formulate Gemini prompt structure
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {"text": f"System Guidelines:\n{system_prompt}\n\nUser Input:\n{user_prompt}"}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.2,
                }
            }
            if json_mode:
                payload["generationConfig"]["responseMimeType"] = "application/json"

            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=15.0)
                if response.status_code == 200:
                    res_data = response.json()
                    return res_data["candidates"][0]["content"]["parts"][0]["text"]
                else:
                    logger.error(f"Gemini API returned error {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"Gemini API Exception: {e}")

    # 2. Try OpenAI API
    if settings.OPENAI_API_KEY:
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}"
            }
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.2
            }
            if json_mode:
                payload["response_format"] = {"type": "json_object"}

            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=15.0)
                if response.status_code == 200:
                    res_data = response.json()
                    return res_data["choices"][0]["message"]["content"]
                else:
                    logger.error(f"OpenAI API returned error {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"OpenAI API Exception: {e}")

    # 3. Fallback Local Simulation Engine
    return simulate_agent_response(system_prompt, user_prompt, json_mode)

def simulate_agent_response(system_prompt: str, user_prompt: str, json_mode: bool) -> str:
    """Provides high-fidelity offline/simulated responses in various Indian languages based on user query analysis."""
    text = user_prompt.lower()
    
    # JSON Mode is typically used by the Orchestrator
    if json_mode:
        # Check intent keyword clues
        if "translate" in text or "explain word" in text or "meaning" in text:
            agent = "TRANSLATOR"
        elif "plan" in text or "todo" in text or "schedule" in text or "make a list" in text:
            agent = "PLANNER"
        elif "weather" in text or "search" in text or "news" in text or "lookup" in text:
            agent = "SEARCH"
        elif "teach" in text or "learn" in text or "study" in text or "explain how" in text:
            agent = "TUTOR"
        elif "document" in text or "pdf" in text or "file" in text or "knowledge" in text or "my notes" in text:
            agent = "KNOWLEDGE_RAG"
        else:
            agent = "GENERAL_ASSISTANT"
            
        return json.dumps({
            "agent": agent,
            "reason": "Simulated intent classification based on user query heuristics."
        })

    # If it's a specific agent prompt, construct native responses
    # Detect language of user query or fallback
    lang = "english"
    if any(k in text for k in ["tamil", "vanakkam", "epdi", "nalla"]):
        lang = "tamil"
    elif any(k in text for k in ["namaste", "hindi", "kya", "kaise"]):
        lang = "hindi"
    elif any(k in text for k in ["telugu", "namaskaram", "ela"]):
        lang = "telugu"
    elif any(k in text for k in ["bengali", "kemon", "ami"]):
        lang = "bengali"

    # Translator Agent
    if "translation and code-switching" in system_prompt.lower():
        if lang == "tamil":
            return "Translation result:\nScript: வணக்கம், நீங்கள் எப்படி இருக்கிறீர்கள்?\nTransliteration: Vanakkam, neenga eppadi irukkinga?\nEnglish: Hello, how are you?"
        elif lang == "hindi":
            return "Translation result:\nScript: नमस्ते, आप कैसे हैं?\nTransliteration: Namaste, aap kaise hain?\nEnglish: Hello, how are you?"
        return "Translation result:\nScript: Hello, how are you?\nExplanation: Standard greeting across all target languages."

    # Planner Agent
    if "planning and automation" in system_prompt.lower():
        if lang == "tamil":
            return "உங்களுக்கான திட்டமிடல் (Your Plan):\n1. குறிப்பைச் சேமிக்கவும் (Save notes)\n2. நாளை காலை 9 மணிக்கு நினைவூட்டல் அமைக்கவும் (Set reminder for tomorrow 9 AM)\n3. கூட்டத்திற்கான மின்னஞ்சல் அனுப்பவும் (Send meeting email)"
        elif lang == "hindi":
            return "आपकी योजना (Your Plan):\n1. नोट सहेजें (Save notes)\n2. कल सुबह 9 बजे रिमाइंडर सेट करें (Set reminder for tomorrow 9 AM)\n3. मीटिंग ईमेल भेजें (Send meeting email)"
        return "Your Structured Plan:\n1. Create task list item\n2. Set reminder for tomorrow at 9:00 AM\n3. Notify user of upcoming events"

    # Search Agent
    if "search agent" in system_prompt.lower():
        return "Search Results:\nFound recent local updates. Simulating response:\n- Today's local temperature is 28°C with high humidity.\n- Local transport is operating on standard schedules.\n- Source: Local Weather Portal."

    # Tutor Agent
    if "language tutor" in system_prompt.lower():
        if lang == "tamil":
            return "வணக்கம் மாணவரே! (Hello Student!)\nஇன்று நாம் அடிப்படை தமிழ் வார்த்தைகளை படிப்போம்:\n- நன்றி (Nandri) = Thank you\n- வரவற்கிறேன் (Varaverkirain) = Welcome\nஏதேனும் சந்தேகம் இருந்தால் கேளுங்கள்!"
        elif lang == "hindi":
            return "नमस्ते छात्र! (Hello Student!)\nआज हम बुनियादी हिंदी शब्द सीखेंगे:\n- धन्यवाद (Dhanyavaad) = Thank you\n- स्वागत है (Swaagat hai) = Welcome\nकोई प्रश्न हो तो अवश्य पूछें!"
        return "Welcome to the tutor session! We will practice local phrasing and grammar structures today."

    # Knowledge RAG Agent
    if "knowledge platform agent" in system_prompt.lower():
        return "Based on your uploaded documents [UserDocument.pdf - Chunk 1]: The system defaults, profile settings, and accessibility metrics are active. Let me know if you would like me to extract more details."

    # General Assistant
    if lang == "tamil":
        return "வணக்கம்! நான் லிங்கோஸ்பியர் AI. உங்களுக்கு நான் எவ்வாறு உதவ முடியும்? (Hello! I am LingoSphere AI. How can I help you today?)"
    elif lang == "hindi":
        return "नमस्ते! मैं लिंगोस्फीयर AI हूँ। आज मैं आपकी क्या सहायता कर सकता हूँ? (Hello! I am LingoSphere AI. How can I help you today?)"
    elif lang == "telugu":
        return "నమస్కారం! నేను లింగోస్పియర్ AI. మీకు నేను ఎలా సహాయపడగలను? (Hello! I am LingoSphere AI. How can I help you today?)"
    elif lang == "bengali":
        return "নমস্কার! আমি লিঙ্গোস্ফিয়ার AI। আজ আমি আপনাকে কীভাবে সাহায্য করতে পারি? (Hello! I am LingoSphere AI. How can I help you today?)"
        
    return "Hello! I am LingoSphere AI. I am ready to assist you in your local language (Tamil, Hindi, Telugu, Malayalam, Kannada, Bengali, or English)."
