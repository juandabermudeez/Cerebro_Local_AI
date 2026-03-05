from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
from pydantic import BaseModel
import sqlite3
import os

app = FastAPI(title="Cerebro Local AI API", version="2.1")

# Habilitar el servicio de archivos estáticos para visualizar fotos y documentos
# Asegurarse de que las rutas existen
if not os.path.exists("fotos_locales"): os.makedirs("fotos_locales")
if not os.path.exists("documentos_locales"): os.makedirs("documentos_locales")

app.mount("/fotos", StaticFiles(directory="fotos_locales"), name="fotos")
app.mount("/documentos", StaticFiles(directory="documentos_locales"), name="documentos")

# Pydantic models
class RecursoUpdate(BaseModel):
    contenido: Optional[str] = None
    etiqueta: Optional[str] = None
    favorito: Optional[bool] = None

# Permitir CORS para el frontend (Vite/React usualmente corre en 5173 o 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, esto debería restringirse
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cerebro_ai.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/")
def read_root():
    return {"message": "Bienvenido a la API de Cerebro Local AI"}

@app.get("/api/stats")
def get_stats():
    """Obtiene estadísticas generales para el dashboard"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM datos")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT tipo, COUNT(*) FROM datos GROUP BY tipo")
        por_tipo = {row['tipo']: row['COUNT(*)'] for row in cursor.fetchall()}
        
        # Stats de la semana
        cursor.execute("SELECT COUNT(*) FROM datos WHERE DATE(fecha) >= DATE('now', '-7 days')")
        semana = cursor.fetchone()[0]
        
        # Top etiquetas
        cursor.execute('''
            SELECT etiqueta, COUNT(*) as count 
            FROM datos 
            WHERE etiqueta IS NOT NULL AND etiqueta != 'SinEtiqueta'
            GROUP BY etiqueta 
            ORDER BY count DESC 
            LIMIT 5
        ''')
        top_etiquetas = [{"etiqueta": row["etiqueta"], "count": row["count"]} for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            "total": total,
            "por_tipo": por_tipo,
            "esta_semana": semana,
            "top_etiquetas": top_etiquetas
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/recursos")
def get_recursos(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    tipo: Optional[str] = None,
    favorito: Optional[bool] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    order: str = Query("desc", regex="^(asc|desc)$")
):
    """Obtiene la lista de recursos con soporte para paginación, búsqueda y filtros avanzados"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM datos WHERE 1=1"
        params = []
        
        if search:
            query += " AND (contenido LIKE ? OR etiqueta LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
            
        if tipo:
            query += " AND tipo = ?"
            params.append(tipo)
            
        if favorito is not None:
            fav_int = 1 if favorito else 0
            query += " AND favorito = ?"
            params.append(fav_int)

        if date_from:
            query += " AND DATE(fecha) >= DATE(?)"
            params.append(date_from)
            
        if date_to:
            query += " AND DATE(fecha) <= DATE(?)"
            params.append(date_to)
            
        # Obtener el total antes de paginar
        count_query = query.replace("SELECT *", "SELECT COUNT(*)")
        cursor.execute(count_query, params)
        total_items = cursor.fetchone()[0]
        
        # Aplicar orden y paginación
        query += f" ORDER BY fecha {order.upper()} LIMIT ? OFFSET ?"
        params.extend([limit, skip])
        
        cursor.execute(query, params)
        items = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            "items": items,
            "total": total_items,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/recursos/{item_id}")
def update_recurso(item_id: int, update: RecursoUpdate):
    """Actualiza los campos de un recurso (edición)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Construir query dinámica
        fields = []
        params = []
        if update.contenido is not None:
            fields.append("contenido = ?")
            params.append(update.contenido)
        if update.etiqueta is not None:
            fields.append("etiqueta = ?")
            params.append(update.etiqueta)
        if update.favorito is not None:
            fields.append("favorito = ?")
            params.append(1 if update.favorito else 0)
            
        if not fields:
            raise HTTPException(status_code=400, detail="Nada que actualizar")
            
        params.append(item_id)
        query = f"UPDATE datos SET {', '.join(fields)} WHERE id = ?"
        
        cursor.execute(query, params)
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Recurso no encontrado")
            
        conn.commit()
        conn.close()
        
        return {"status": "success", "id": item_id}
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/recursos/{item_id}/favorito")
def toggle_favorito(item_id: int):
    """Alterna el estado de favorito de un recurso"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT favorito FROM datos WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail="Recurso no encontrado")
            
        nuevo_estado = 1 if row['favorito'] == 0 else 0
        cursor.execute("UPDATE datos SET favorito = ? WHERE id = ?", (nuevo_estado, item_id))
        conn.commit()
        conn.close()
        
        return {"id": item_id, "favorito": nuevo_estado}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/recursos/{item_id}")
def delete_recurso(item_id: int):
    """Elimina un recurso de la base de datos (y su archivo asociado si aplica)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT tipo, contenido FROM datos WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail="Recurso no encontrado")
            
        # Intentar borrar el archivo físico primero
        tipo = row['tipo']
        contenido = row['contenido']
        
        if tipo in ['foto', 'pdf'] and '\nArchivo: ' in contenido:
            ruta_archivo = contenido.split('\nArchivo: ', 1)[1].strip()
            # La ruta guardada es relativa al directorio raíz (ej: fotos_locales/...)
            ruta_completa = os.path.join(os.path.dirname(os.path.dirname(__file__)), ruta_archivo)
            if os.path.exists(ruta_completa):
                try:
                    os.remove(ruta_completa)
                except Exception as e:
                    print(f"Error borrando archivo {ruta_completa}: {e}")
                    
        # Borrar el registro
        cursor.execute("DELETE FROM datos WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()
        
        return {"status": "success", "message": f"Recurso {item_id} eliminado"}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Para pruebas locales puedes correr el script directamente
    # Python intentará buscar la db en el padre temporalmente
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
