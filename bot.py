import telebot
import os
from dotenv import load_dotenv
from database import CerebroDB
import re
from datetime import datetime
import urllib.request
import uuid
import logging

# Configurar el sistema de logging
if not os.path.exists('logs'):
    os.makedirs('logs')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# Obtener el token del archivo .env
TOKEN = os.getenv('TELEGRAM_TOKEN')

if not TOKEN or TOKEN == 'AQUI_VA_TU_TOKEN':
    logger.error("Token no configurado en el archivo .env")
    logger.info("Por favor, asegúrate de reemplazar 'AQUI_VA_TU_TOKEN' con tu token real de @BotFather")
    exit()

# Inicializar el bot
bot = telebot.TeleBot(TOKEN)

# Inicializar la base de datos
db = CerebroDB()

# Crear carpetas si no existen
FOTOS_DIR = "fotos_locales"
DOCS_DIR = "documentos_locales"
if not os.path.exists(FOTOS_DIR):
    os.makedirs(FOTOS_DIR)
if not os.path.exists(DOCS_DIR):
    os.makedirs(DOCS_DIR)

def descargar_y_guardar_foto(file_id, caption=""):
    """Descarga una foto de Telegram y la guarda localmente"""
    try:
        # Obtener información del archivo
        file_info = bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
        
        # Generar nombre único
        extension = ".jpg" if file_info.file_path.endswith(".jpg") else ".png" if file_info.file_path.endswith(".png") else ".jpg"
        filename = f"foto_{uuid.uuid4().hex[:8]}{extension}"
        filepath = os.path.join(FOTOS_DIR, filename)
        
        # Descargar la imagen
        urllib.request.urlretrieve(file_url, filepath)
        
        return filepath
    except Exception as e:
        logger.error(f"Error descargando foto: {str(e)}", exc_info=True)
        return None

def descargar_y_guardar_documento(file_id, filename_original, caption=""):
    """Descarga un documento de Telegram y lo guarda localmente"""
    try:
        # Obtener información del archivo
        file_info = bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
        
        # Generar nombre seguro
        nombre_seguro = filename_original.replace(" ", "_").replace("/", "_")
        filepath = os.path.join(DOCS_DIR, nombre_seguro)
        
        # Descargar el documento
        urllib.request.urlretrieve(file_url, filepath)
        
        return filepath
    except Exception as e:
        logger.error(f"Error descargando documento '{filename_original}': {str(e)}", exc_info=True)
        return None
def es_url(texto):
    """Verifica si un texto es una URL"""
    patron = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
    return re.match(patron, texto) is not None

def es_documento_imagen(filename):
    """Verifica si un documento es una imagen"""
    if not filename:
        return False
    extension = filename.lower().split('.')[-1]
    return extension in ['jpg', 'jpeg', 'png', 'gif', 'webp']

def es_documento_pdf(filename):
    """Verifica si un documento es un PDF"""
    if not filename:
        return False
    extension = filename.lower().split('.')[-1]
    return extension == 'pdf'

def extraer_etiquetas(mensaje):
    """
    Extrae TODOS los hashtags del mensaje usando la Taxonomía de 3 Niveles
    
    Taxonomía definida:
    - Nivel 1 (Proyectos): #LaAgencia, #GreenHouse, #Tesis, #Varios
    - Nivel 2 (Naturaleza): #Prompt, #Novedades, #Aprender, #Herramientas, #CasosDeUso, #LabPersonal, #Hacks  
    - Nivel 3 (Plataformas): #MetaAds, #SEO, #Notion, etc.
    
    Returns: string con etiquetas separadas por coma o "SinEtiqueta" si no hay hashtags
    """
    hashtags = re.findall(r'#(\w+)', mensaje)
    
    if hashtags:
        # Unir todas las etiquetas encontradas separadas por coma
        return ', '.join(hashtags)
    else:
        return "SinEtiqueta"

def limpiar_contenido(mensaje):
    """
    Elimina todos los hashtags del mensaje para guardar solo el contenido limpio
    """
    # Reemplazar todos los hashtags con vacío
    contenido_limpio = re.sub(r'#\w+', '', mensaje).strip()
    return contenido_limpio

@bot.message_handler(commands=['start', 'help'])
def comando_bienvenida(mensaje):
    """Mensaje de bienvenida y ayuda"""
    texto = """
🧠 *Mi Cerebro AI Bot*

¡Hola! Soy tu bot personal para guardar información.

*¿Cómo usarlo?*
• Envía un *link* para guardarlo
• Envía *texto* para guardarlo como nota  
• Envía una *foto* para guardarla

*¿Cómo añadir etiquetas?*
Usa múltiples hashtags con tu Taxonomía de 3 Niveles:
• "https://tool.ai #LaAgencia #Herramientas #Notion"
• "Nuevo prompt para IA #Tesis #Prompt #MetaAds"
• "Artículo SEO #GreenHouse #Novedades #SEO"

*Taxonomía de 3 Niveles:*
• Nivel 1 (Proyectos): #LaAgencia, #GreenHouse, #Tesis, #Varios
• Nivel 2 (Naturaleza): #Prompt, #Novedades, #Aprender, #Herramientas, #CasosDeUso, #LabPersonal, #Hacks  
• Nivel 3 (Plataformas): #MetaAds, #SEO, #Notion, etc.

*Comandos disponibles:*
/start - Este mensaje
/stats - Ver estadísticas
/ultimos - Ver últimos 10 guardados

¡Todo se guarda automáticamente con etiquetas múltiples! 🚀
    """
    bot.reply_to(mensaje, texto, parse_mode='Markdown')

@bot.message_handler(commands=['stats'])
def comando_estadisticas(mensaje):
    """Muestra estadísticas de la base de datos"""
    stats = db.obtener_estadisticas()
    
    texto = f"""
📊 *Estadísticas de tu Cerebro AI*

📁 Total guardado: {stats['total']} elementos

📋 Por tipo:"""
    
    for tipo, cantidad in stats['por_tipo'].items():
        emoji = {"link": "🔗", "texto": "📝", "foto": "🖼️"}.get(tipo, "📄")
        texto += f"\n{emoji} {tipo}: {cantidad}"
    
    if stats['por_etiqueta']:
        texto += "\n\n🏷️ Por etiqueta:"
        for etiqueta, cantidad in stats['por_etiqueta'].items():
            texto += f"\n• #{etiqueta}: {cantidad}"
    
    bot.reply_to(mensaje, texto, parse_mode='Markdown')

@bot.message_handler(commands=['ultimos'])
def comando_ultimos(mensaje):
    """Muestra los últimos 10 elementos guardados"""
    datos = db.obtener_todos_los_datos()[:10]
    
    if not datos:
        bot.reply_to(mensaje, "📭 Aún no tienes nada guardado")
        return
    
    texto = "📝 *Tus últimos 10 guardados:*\n\n"
    
    for i, (id, tipo, contenido, etiqueta, fecha) in enumerate(datos, 1):
        emoji = {"link": "🔗", "texto": "📝", "foto": "🖼️"}.get(tipo, "📄")
        
        # Formatear fecha
        fecha_formateada = datetime.strptime(fecha, '%Y-%m-%d %H:%M:%S').strftime('%d/%m %H:%M')
        
        # Cortar contenido si es muy largo
        contenido_corto = contenido[:50] + "..." if len(contenido) > 50 else contenido
        
        texto += f"{i}. {emoji} {tipo} - {fecha_formateada}\n"
        texto += f"   {contenido_corto}\n"
        if etiqueta:
            texto += f"   🏷️ #{etiqueta}\n"
        texto += "\n"
    
    bot.reply_to(mensaje, texto, parse_mode='Markdown')

@bot.message_handler(content_types=['text'])
def manejar_texto(mensaje):
    """Maneja mensajes de texto (links o notas) con extracción inteligente de etiquetas"""
    try:
        contenido_original = mensaje.text
        
        # Extraer etiquetas usando la Taxonomía de 3 Niveles
        etiquetas = extraer_etiquetas(contenido_original)
        
        # Limpiar el contenido quitando todos los hashtags
        contenido_limpio = limpiar_contenido(contenido_original)
        
        # Determinar si es un link o texto
        if es_url(contenido_limpio):
            db.guardar_dato("link", contenido_limpio, etiquetas)
            respuesta = f"✅ *Link guardado* 🔗\n\n{contenido_limpio}"
            if etiquetas != "SinEtiqueta":
                respuesta += f"\n🏷️ Etiquetas: #{etiquetas.replace(', ', ' #')}"
            else:
                respuesta += f"\n🏷️ {etiquetas}"
        else:
            db.guardar_dato("texto", contenido_limpio, etiquetas)
            respuesta = f"✅ *Texto guardado* 📝\n\n\"{contenido_limpio}\""
            if etiquetas != "SinEtiqueta":
                respuesta += f"\n🏷️ Etiquetas: #{etiquetas.replace(', ', ' #')}"
            else:
                respuesta += f"\n🏷️ {etiquetas}"
        
        bot.reply_to(mensaje, respuesta, parse_mode='Markdown')
        logger.info(f"Mensaje de texto procesado. Etiquetas: {etiquetas}")
        
    except Exception as e:
        logger.error(f"Error procesando mensaje de texto: {str(e)}", exc_info=True)
        bot.reply_to(mensaje, "❌ Ocurrió un error al procesar tu mensaje. Intenta de nuevo.", parse_mode='Markdown')

@bot.message_handler(content_types=['photo'])
def manejar_foto(mensaje):
    """Maneja fotos descargándolas físicamente"""
    try:
        # Obtener la foto de mayor resolución
        foto_info = mensaje.photo[-1]
        file_id = foto_info.file_id
        
        # Extraer etiquetas del caption si existe
        if mensaje.caption:
            etiquetas = extraer_etiquetas(mensaje.caption)
            # Limpiar hashtags del caption para obtener el comentario
            comentario = limpiar_contenido(mensaje.caption)
        else:
            etiquetas = "SinEtiqueta"
            comentario = ""
        
        # Descargar y guardar la foto físicamente
        filepath = descargar_y_guardar_foto(file_id, mensaje.caption)
        
        if filepath:
            # Guardar comentario y ruta con formato: "comentario\nArchivo: ruta"
            if comentario:
                contenido_completo = f"{comentario}\nArchivo: {filepath}"
            else:
                contenido_completo = f"Archivo: {filepath}"
            
            db.guardar_dato("foto", contenido_completo, etiquetas)
            
            # Mensaje de confirmación en HTML
            respuesta = f"🖼️ <b>¡Imagen guardada con éxito!</b>"
            if comentario:
                respuesta += f"\n\n💬 {comentario}"
            respuesta += f"\n📁 Ruta: {filepath}"
            if etiquetas != "SinEtiqueta":
                respuesta += f"\n🏷️ Etiquetas: #{etiquetas.replace(', ', ' #')}"
            else:
                respuesta += f"\n🏷️ {etiquetas}"
            
            logger.info(f"Foto procesada y guardada. Etiquetas: {etiquetas}")
        else:
            respuesta = "❌ Error al guardar la imagen. Intenta de nuevo."
            logger.warning("Fallo la descarga de la foto en manejar_foto")
        
        bot.reply_to(mensaje, respuesta, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Error procesando foto: {str(e)}", exc_info=True)
        bot.reply_to(mensaje, "❌ Ocurrió un error inesperado al guardar la foto.", parse_mode='HTML')

@bot.message_handler(content_types=['document'])
def manejar_documento(mensaje):
    """Maneja documentos, especialmente imágenes y PDFs"""
    try:
        filename = mensaje.document.file_name
        
        # Verificar si es una imagen
        if es_documento_imagen(filename):
            file_id = mensaje.document.file_id
            
            # Extraer etiquetas del caption si existe
            if mensaje.caption:
                etiquetas = extraer_etiquetas(mensaje.caption)
                # Limpiar hashtags del caption para obtener el comentario
                comentario = limpiar_contenido(mensaje.caption)
            else:
                etiquetas = "SinEtiqueta"
                comentario = ""
            
            # Descargar y guardar la imagen
            filepath = descargar_y_guardar_foto(file_id, mensaje.caption)
            
            if filepath:
                # Guardar comentario y ruta con formato: "comentario\nArchivo: ruta"
                if comentario:
                    contenido_completo = f"{comentario}\nArchivo: {filepath}"
                else:
                    contenido_completo = f"Archivo: {filepath}"
                
                db.guardar_dato("foto", contenido_completo, etiquetas)
                
                # Mensaje de confirmación en HTML
                respuesta = f"🖼️ <b>¡Imagen (documento) guardada con éxito!</b>"
                if comentario:
                    respuesta += f"\n\n💬 {comentario}"
                respuesta += f"\n📁 Ruta: {filepath}"
                if etiquetas != "SinEtiqueta":
                    respuesta += f"\n🏷️ Etiquetas: #{etiquetas.replace(', ', ' #')}"
                else:
                    respuesta += f"\n🏷️ {etiquetas}"
                logger.info(f"Documento imagen procesado y guardado. Etiquetas: {etiquetas}")
            else:
                respuesta = "❌ Error al guardar la imagen. Intenta de nuevo."
                logger.warning(f"Fallo la descarga de la imagen documento '{filename}'")
        
        # Verificar si es un PDF
        elif es_documento_pdf(filename):
            file_id = mensaje.document.file_id
            
            # Extraer etiquetas del caption si existe
            if mensaje.caption:
                etiquetas = extraer_etiquetas(mensaje.caption)
                # Limpiar hashtags del caption para obtener el comentario
                comentario = limpiar_contenido(mensaje.caption)
            else:
                etiquetas = "SinEtiqueta"
                comentario = ""
            
            # Descargar y guardar el PDF
            filepath = descargar_y_guardar_documento(file_id, filename, mensaje.caption)
            
            if filepath:
                # Guardar comentario y ruta con formato: "comentario\nArchivo: ruta"
                if comentario:
                    contenido_completo = f"{comentario}\nArchivo: {filepath}"
                else:
                    contenido_completo = f"Archivo: {filepath}"
                
                db.guardar_dato("pdf", contenido_completo, etiquetas)
                
                # Mensaje de confirmación en HTML
                respuesta = f"📄 <b>¡PDF guardado con éxito!</b>"
                if comentario:
                    respuesta += f"\n\n💬 {comentario}"
                respuesta += f"\n📁 Ruta: {filepath}"
                if etiquetas != "SinEtiqueta":
                    respuesta += f"\n🏷️ Etiquetas: #{etiquetas.replace(', ', ' #')}"
                else:
                    respuesta += f"\n🏷️ {etiquetas}"
                logger.info(f"PDF procesado y guardado. Etiquetas: {etiquetas}")
            else:
                respuesta = "❌ Error al guardar el PDF. Intenta de nuevo."
                logger.warning(f"Fallo la descarga del documento PDF '{filename}'")
        
        else:
            respuesta = f"❓ El archivo '{filename}' no es compatible. Solo acepto: JPG, PNG, GIF, WebP y PDF"
            logger.info(f"Intento de subida de archivo no compatible: {filename}")
        
        bot.reply_to(mensaje, respuesta, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Error procesando documento: {str(e)}", exc_info=True)
        bot.reply_to(mensaje, "❌ Ocurrió un error inesperado al procesar el documento.", parse_mode='HTML')

@bot.message_handler(func=lambda message: True)
def manejar_otros(mensaje):
    """Maneja otros tipos de mensajes"""
    bot.reply_to(mensaje, "❓ Solo puedo guardar texto, links, fotos, imágenes y PDFs por ahora", parse_mode='HTML')

def main():
    """Función principal para iniciar el bot"""
    logger.info("Iniciando Mi Cerebro AI Bot...")
    logger.info(f"Bot conectado con token: {TOKEN[:10]}...")
    logger.info("Esperando mensajes...")
    
    try:
        # Iniciar el bot
        bot.polling(none_stop=True)
    except Exception as e:
        logger.critical(f"Error fatal en el bot: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()
