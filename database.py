import sqlite3
import os
import shutil
from datetime import datetime


class CerebroDB:
    def __init__(self):
        self.db_name = "cerebro_ai.db"
        self.init_database()
        self.generar_backup()  # Backup automático al iniciar
    
    def init_database(self):
        """Crea la base de datos y la tabla si no existen"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS datos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo TEXT NOT NULL,
                    contenido TEXT NOT NULL,
                    etiqueta TEXT,
                    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    favorito INTEGER DEFAULT 0
                )
            ''')
            
            # Añadir columna favorito si no existe
            try:
                cursor.execute("ALTER TABLE datos ADD COLUMN favorito INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass  # Columna ya existe
    
    def guardar_dato(self, tipo, contenido, etiqueta=None):
        """Guarda un nuevo dato en la base de datos"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO datos (tipo, contenido, etiqueta) VALUES (?, ?, ?)', (tipo, contenido, etiqueta))
    
    def obtener_todos_los_datos(self):
        """Obtiene todos los datos de la base de datos"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, tipo, contenido, etiqueta, fecha, favorito FROM datos ORDER BY fecha DESC')
            return cursor.fetchall()
    
    def obtener_datos_por_tipo(self, tipo):
        """Filtra datos por tipo (link, texto, foto)"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, tipo, contenido, etiqueta, fecha, favorito FROM datos WHERE tipo = ? ORDER BY fecha DESC', (tipo,))
            return cursor.fetchall()
    
    def obtener_datos_por_etiqueta(self, etiqueta):
        """Filtra datos por etiqueta"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, tipo, contenido, etiqueta, fecha, favorito FROM datos WHERE etiqueta = ? ORDER BY fecha DESC', (etiqueta,))
            return cursor.fetchall()
    
    def obtener_estadisticas(self):
        """Obtiene estadísticas básicas de la base de datos"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            # Total de registros
            cursor.execute("SELECT COUNT(*) FROM datos")
            total = cursor.fetchone()[0]

            # Distribución por tipo
            cursor.execute("SELECT tipo, COUNT(*) FROM datos GROUP BY tipo")
            por_tipo = dict(cursor.fetchall())

            # Distribución completa por etiqueta (para el bot / stats generales)
            cursor.execute(
                "SELECT etiqueta, COUNT(*) FROM datos "
                "WHERE etiqueta IS NOT NULL GROUP BY etiqueta"
            )
            por_etiqueta = dict(cursor.fetchall())

            # Top etiquetas (excluyendo 'SinEtiqueta'), para el dashboard
            cursor.execute(
                """
                SELECT etiqueta, COUNT(*) as count 
                FROM datos 
                WHERE etiqueta IS NOT NULL AND etiqueta != 'SinEtiqueta'
                GROUP BY etiqueta 
                ORDER BY count DESC 
                LIMIT 3
                """
            )
            top_etiquetas = cursor.fetchall()

            return {
                "total": total,
                "por_tipo": por_tipo,
                "por_etiqueta": por_etiqueta,
                "top_etiquetas": top_etiquetas,
            }

    def toggle_favorito(self, id):
        """Cambia el estado de favorito de 0 a 1 o viceversa"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT favorito FROM datos WHERE id = ?", (id,))
            resultado = cursor.fetchone()
            
            if resultado:
                nuevo_estado = 1 if resultado[0] == 0 else 0
                cursor.execute("UPDATE datos SET favorito = ? WHERE id = ?", (nuevo_estado, id))
                return nuevo_estado
        return None
    
    def actualizar_contenido(self, id, nuevo_contenido):
        """Actualiza el contenido de un recurso"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE datos SET contenido = ? WHERE id = ?", (nuevo_contenido, id))
            return cursor.rowcount > 0

    def obtener_estadisticas_temporales(self):
        """Obtiene métricas de productividad temporal (hoy, semana)"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT COUNT(*) FROM datos 
                WHERE DATE(fecha) = DATE('now')
                """
            )
            recursos_hoy = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT COUNT(*) FROM datos 
                WHERE DATE(fecha) >= DATE('now', '-7 days')
                """
            )
            recursos_semana = cursor.fetchone()[0]

            return {
                "recursos_hoy": recursos_hoy,
                "recursos_semana": recursos_semana,
            }

    def obtener_datos_por_filtro_tiempo(self, filtro):
        """Obtiene datos filtrados por rango temporal predefinido"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            if filtro == "Todo":
                cursor.execute(
                    """
                    SELECT id, tipo, contenido, etiqueta, fecha, favorito 
                    FROM datos 
                    ORDER BY fecha DESC
                    """
                )
            elif filtro == "Hoy":
                cursor.execute(
                    """
                    SELECT id, tipo, contenido, etiqueta, fecha, favorito 
                    FROM datos 
                    WHERE DATE(fecha) = DATE('now') 
                    ORDER BY fecha DESC
                    """
                )
            elif filtro == "Esta semana":
                cursor.execute(
                    """
                    SELECT id, tipo, contenido, etiqueta, fecha, favorito 
                    FROM datos 
                    WHERE DATE(fecha) >= DATE('now', '-7 days') 
                    ORDER BY fecha DESC
                    """
                )
            else:
                # Filtro no reconocido: devolver todo
                cursor.execute(
                    """
                    SELECT id, tipo, contenido, etiqueta, fecha, favorito 
                    FROM datos 
                    ORDER BY fecha DESC
                    """
                )

            return cursor.fetchall()

    def obtener_datos_con_filtros(self, filtro_tiempo, etiquetas_seleccionadas=None):
        """Obtiene datos aplicando filtro temporal y por etiquetas (para dashboard u otros clientes)"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            consulta = """
                SELECT id, tipo, contenido, etiqueta, fecha, favorito 
                FROM datos 
                WHERE 1=1
            """
            params = []

            if filtro_tiempo == "Hoy":
                consulta += " AND DATE(fecha) = DATE('now')"
            elif filtro_tiempo == "Esta semana":
                consulta += " AND DATE(fecha) >= DATE('now', '-7 days')"

            if etiquetas_seleccionadas:
                condiciones = []
                for etiqueta in etiquetas_seleccionadas:
                    condiciones.append("etiqueta LIKE ?")
                    params.append(f"%{etiqueta}%")
                consulta += " AND (" + " OR ".join(condiciones) + ")"

            consulta += " ORDER BY fecha DESC"
            cursor.execute(consulta, params)
            return cursor.fetchall()

    def obtener_todas_las_etiquetas_unicas(self):
        """Devuelve todas las etiquetas únicas (ya separadas) distintas de 'SinEtiqueta'"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT DISTINCT etiqueta 
                FROM datos 
                WHERE etiqueta IS NOT NULL AND etiqueta != 'SinEtiqueta'
                ORDER BY etiqueta
                """
            )
            etiquetas_brutas = cursor.fetchall()

        etiquetas_unicas = set()
        for etiquetas in etiquetas_brutas:
            etiquetas_individuales = [
                etiqueta.strip() for etiqueta in etiquetas[0].split(",")
            ]
            etiquetas_unicas.update(etiquetas_individuales)

        return sorted(list(etiquetas_unicas))
    
    def generar_backup(self):
        """Genera un backup automático de la base de datos"""
        try:
            # Crear carpeta de backups si no existe
            backups_dir = "backups_seguridad"
            if not os.path.exists(backups_dir):
                os.makedirs(backups_dir)
            
            # Generar nombre de archivo con fecha actual
            fecha_actual = datetime.now().strftime("%Y_%m_%d")
            nombre_backup = f"respaldo_{fecha_actual}.db"
            ruta_backup = os.path.join(backups_dir, nombre_backup)
            
            # Copiar archivo de base de datos
            shutil.copy2(self.db_name, ruta_backup)
            
            # Limpiar backups viejos (mantener solo los 5 más recientes)
            self.limpiar_backups_viejos(backups_dir)
            
        except Exception as e:
            # Silencioso para no interrumpir el programa
            pass
    
    def limpiar_backups_viejos(self, backups_dir):
        """Mantiene solo los 5 backups más recientes y elimina los más viejos"""
        try:
            # Obtener todos los archivos de backup
            archivos_backup = []
            for archivo in os.listdir(backups_dir):
                if archivo.startswith("respaldo_") and archivo.endswith(".db"):
                    ruta_completa = os.path.join(backups_dir, archivo)
                    fecha_modificacion = os.path.getmtime(ruta_completa)
                    archivos_backup.append((ruta_completa, fecha_modificacion))
            
            # Ordenar por fecha de modificación (más reciente primero)
            archivos_backup.sort(key=lambda x: x[1], reverse=True)
            
            # Eliminar backups viejos si hay más de 5
            if len(archivos_backup) > 5:
                for archivo, _ in archivos_backup[5:]:
                    try:
                        os.remove(archivo)
                    except:
                        pass  # Silencioso si no se puede eliminar
                        
        except Exception:
            # Silencioso para no interrumpir el programa
            pass

# Para probar la base de datos
if __name__ == "__main__":
    db = CerebroDB()
    
    # Datos de prueba
    db.guardar_dato("link", "https://ejemplo.com", "tecnología")
    db.guardar_dato("texto", "Este es un texto de prueba", "notas")
    db.guardar_dato("foto", "ruta/a/imagen.jpg", "imágenes")
    
    # Mostrar estadísticas
    stats = db.obtener_estadisticas()
    print("\nEstadísticas:")
    print(f"Total de datos: {stats['total']}")
    print(f"Por tipo: {stats['por_tipo']}")
    print(f"Por etiqueta: {stats['por_etiqueta']}")
