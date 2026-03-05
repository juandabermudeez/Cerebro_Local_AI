import os
import httpx
import json
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
# Por defecto usaremos Qwen 1.5B si es local, ya que es muy liviano para los 4GB VRAM
LOCAL_MODEL = os.getenv("LOCAL_MODEL", "qwen2.5:1.5b") 

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

async def ask_local_ai(prompt: str, system_prompt: str = "Eres un asistente útil y conciso.") -> str:
    """Consulta a Ollama localmente"""
    try:
        payload = {
            "model": LOCAL_MODEL,
            "prompt": f"System: {system_prompt}\nUser: {prompt}",
            "stream": False
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(OLLAMA_URL, json=payload)
            if response.status_code == 200:
                return response.json().get("response", "").strip()
            return "Error: Ollama no respondió correctamente."
    except Exception as e:
        return f"Error: No se pudo conectar con la IA local (Ollama). ¿Está corriendo? {str(e)}"

async def ask_remote_ai(prompt: str, system_prompt: str = "Eres un asistente experto.") -> str:
    """Consulta a la API de DeepSeek"""
    if not DEEPSEEK_API_KEY:
        return "Error: No hay API Key de DeepSeek configurada."
    
    try:
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(DEEPSEEK_URL, json=payload, headers=headers)
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"].strip()
            return f"Error API: {response.text}"
    except Exception as e:
        return f"Error remoto: {str(e)}"

async def summarize_content(text: str) -> str:
    """Resume un texto largo"""
    system_prompt = "Resume el siguiente texto en máximo 3 puntos clave o un párrafo corto. Sé muy directo y profesional en español."
    
    # Intentamos remoto primero si hay key (mejor calidad), si no local
    if DEEPSEEK_API_KEY:
        return await ask_remote_ai(text, system_prompt)
    return await ask_local_ai(text, system_prompt)

async def suggest_tags(text: str) -> List[str]:
    """Sugiere etiquetas basadas en el contenido"""
    system_prompt = """Analiza el texto y devuelve únicamente una lista de 3 a 5 etiquetas separadas por comas que lo describan. 
    Usa etiquetas en español. No añadas explicaciones, solo las palabras."""
    
    response = ""
    if DEEPSEEK_API_KEY:
        response = await ask_remote_ai(text, system_prompt)
    else:
        response = await ask_local_ai(text, system_prompt)
    
    # Limpiar respuesta para obtener una lista
    tags = [t.strip().replace("#", "") for t in response.split(",")]
    return tags[:5]
