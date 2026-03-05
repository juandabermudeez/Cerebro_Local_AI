import os
import httpx
import json
import sqlite3
from typing import List, Optional, Dict
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

# ─── Config ───────────────────────────────────────────────
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
LOCAL_MODEL = os.getenv("LOCAL_MODEL", "qwen2.5:1.5b")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cerebro_ai.db")

# ─── Low-level AI calls ──────────────────────────────────
async def _call_ollama(prompt: str, system_prompt: str) -> str:
    try:
        payload = {
            "model": LOCAL_MODEL,
            "prompt": f"System: {system_prompt}\nUser: {prompt}",
            "stream": False
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(OLLAMA_URL, json=payload)
            if r.status_code == 200:
                return r.json().get("response", "").strip()
    except Exception as e:
        logger.warning(f"Ollama unavailable: {e}")
    return ""

async def _call_deepseek(prompt: str, system_prompt: str) -> str:
    if not DEEPSEEK_API_KEY:
        return ""
    try:
        headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(DEEPSEEK_URL, json=payload, headers=headers)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
            else:
                logger.warning(f"DeepSeek HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        logger.warning(f"DeepSeek unavailable: {e}")
    return ""

# ─── Smart Fallback ──────────────────────────────────────
async def ask_ai(prompt: str, system_prompt: str = "Eres un asistente útil y conciso. Responde siempre en español.") -> str:
    """Intenta DeepSeek primero, si falla usa Ollama, si ambos fallan devuelve error."""
    # Try remote first (better quality)
    result = await _call_deepseek(prompt, system_prompt)
    if result:
        return result
    # Fallback to local
    result = await _call_ollama(prompt, system_prompt)
    if result:
        return result
    return "⚠️ No hay motor de IA disponible. Configura DEEPSEEK_API_KEY en .env o inicia Ollama."

# ─── AI Status ───────────────────────────────────────────
async def check_ai_status() -> Dict:
    """Verifica qué motores de IA están disponibles."""
    status = {"deepseek": False, "ollama": False, "active_engine": "none"}
    
    if DEEPSEEK_API_KEY:
        test = await _call_deepseek("Responde solo OK", "Responde exactamente OK")
        if test:
            status["deepseek"] = True
            status["active_engine"] = "deepseek"
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get("http://localhost:11434/api/tags")
            if r.status_code == 200:
                status["ollama"] = True
                if status["active_engine"] == "none":
                    status["active_engine"] = "ollama"
    except:
        pass
    
    return status

# ─── Feature 1: Summarize ───────────────────────────────
async def summarize_content(text: str) -> str:
    system = "Resume el siguiente texto en máximo 3 puntos clave. Sé directo y profesional en español."
    return await ask_ai(text[:3000], system)

# ─── Feature 2: Suggest Tags ────────────────────────────
async def suggest_tags(text: str) -> List[str]:
    system = """Analiza el texto y devuelve SOLO una lista de 3-5 etiquetas separadas por comas en español.
Prioriza etiquetas de esta taxonomía si aplican:
Nivel 1: LaAgencia, MiMarcaPersonal, Varios
Nivel 2: Ideas, Herramientas, Referencias, Proyectos, Novedades, Prompt, Aprender, CasosDeUso
No añadas explicaciones, solo las palabras separadas por comas."""
    
    response = await ask_ai(text[:2000], system)
    tags = [t.strip().replace("#", "") for t in response.split(",") if t.strip()]
    return tags[:5]

# ─── Feature 3: Semantic Search ─────────────────────────
def _get_recent_resources(limit=50) -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, tipo, contenido, etiqueta, fecha FROM datos ORDER BY fecha DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

async def semantic_search(query: str) -> List[int]:
    """Busca recursos por significado usando IA."""
    resources = _get_recent_resources(80)
    
    # Build a compact index for the AI
    index_lines = []
    for r in resources:
        short = r["contenido"][:120].replace("\n", " ")
        tags = r["etiqueta"] or "SinEtiqueta"
        index_lines.append(f'[ID:{r["id"]}] ({r["tipo"]}) {short} | Tags: {tags}')
    
    index_text = "\n".join(index_lines)
    
    system = """Eres un buscador semántico. El usuario tiene una base de datos de recursos.
Te daré la lista de recursos y una pregunta. Devuelve SOLO los IDs de los recursos más relevantes (máximo 10), separados por comas.
Si no hay resultados relevantes, responde "NINGUNO". No añadas explicaciones."""
    
    prompt = f"PREGUNTA: {query}\n\nRECURSOS:\n{index_text}"
    
    response = await ask_ai(prompt, system)
    
    if "NINGUNO" in response.upper():
        return []
    
    # Parse IDs from response
    import re
    ids = re.findall(r'\d+', response)
    return [int(i) for i in ids[:10]]

# ─── Feature 4: Weekly Digest ───────────────────────────
async def generate_weekly_digest() -> str:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT tipo, contenido, etiqueta, fecha FROM datos 
        WHERE DATE(fecha) >= DATE('now', '-7 days')
        ORDER BY fecha DESC
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    if not rows:
        return "📭 No guardaste nada esta semana. ¡A capturar ideas!"
    
    # Build compact summary of the week
    lines = []
    for r in rows:
        short = r["contenido"][:100].replace("\n", " ")
        tags = r["etiqueta"] or ""
        lines.append(f'- ({r["tipo"]}) {short} [{tags}]')
    
    week_text = "\n".join(lines)
    
    system = """Eres un asistente de productividad. Genera un resumen semanal ejecutivo en español.
Agrupa los recursos por categoría/tema. Usa emojis. Incluye:
1. Resumen general (1 línea)
2. Agrupación por temas (máx 5 grupos)
3. Dato curioso o patrón detectado
Sé conciso pero informativo."""
    
    return await ask_ai(f"Estos son los {len(rows)} recursos guardados esta semana:\n{week_text}", system)

# ─── Feature 5: Chat with Notes (RAG lite) ──────────────
async def chat_with_notes(question: str) -> str:
    """Responde preguntas sobre la base de datos del usuario."""
    resources = _get_recent_resources(60)
    
    context_lines = []
    for r in resources:
        short = r["contenido"][:150].replace("\n", " ")
        tags = r["etiqueta"] or ""
        context_lines.append(f'[{r["tipo"]}] [{r["fecha"]}] {short} | Tags: {tags}')
    
    context = "\n".join(context_lines)
    
    system = """Eres el asistente personal "Cerebro AI". El usuario te pregunta sobre sus notas, links, fotos y PDFs guardados.
Responde basándote SOLO en el contexto proporcionado. Si no encuentras la información, dilo honestamente.
Responde en español, sé conciso y útil. Usa emojis cuando sea apropiado."""
    
    prompt = f"CONTEXTO (mis recursos guardados):\n{context}\n\nMI PREGUNTA: {question}"
    return await ask_ai(prompt, system)

# ─── Feature 6: Bulk Auto-Tag ───────────────────────────
async def auto_tag_single(text: str) -> str:
    """Tags a single resource and returns comma-separated tags."""
    tags = await suggest_tags(text)
    return ", ".join(tags) if tags else "SinEtiqueta"

async def bulk_auto_tag() -> Dict:
    """Tags all resources that have 'SinEtiqueta'."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, contenido FROM datos WHERE etiqueta IS NULL OR etiqueta = 'SinEtiqueta'")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    results = {"total": len(rows), "tagged": 0, "errors": 0}
    
    for row in rows:
        try:
            tags = await auto_tag_single(row["contenido"])
            if tags and tags != "SinEtiqueta":
                conn2 = sqlite3.connect(DB_PATH)
                conn2.execute("UPDATE datos SET etiqueta = ? WHERE id = ?", (tags, row["id"]))
                conn2.commit()
                conn2.close()
                results["tagged"] += 1
        except Exception as e:
            logger.error(f"Error auto-tagging ID {row['id']}: {e}")
            results["errors"] += 1
    
    return results
