import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os
import shutil
import subprocess
from database import CerebroDB

# Configuración de la página
st.set_page_config(
    page_title="Cerebro Local AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Taxonomía centralizada
TAXONOMIA = {
    'nivel_1': ['LaAgencia', 'GreenHouse', 'Tesis', 'Varios'],
    'nivel_2': ['Prompt', 'Novedades', 'Aprender', 'Herramientas', 'CasosDeUso', 'LabPersonal', 'Hacks']
}


def aplicar_busqueda_sobre_lista(datos, termino_busqueda):
    """Filtra una lista de tuplas de datos por texto de búsqueda en contenido y etiquetas."""
    if not termino_busqueda or not termino_busqueda.strip() or not datos:
        return datos

    df = pd.DataFrame(
        datos,
        columns=['ID', 'Tipo', 'Contenido', 'Etiquetas', 'Fecha', 'Favorito']
    )
    mascara = (
        df['Contenido'].str.contains(termino_busqueda, case=False, na=False)
        | df['Etiquetas'].str.contains(termino_busqueda, case=False, na=False)
    )
    return df[mascara].values.tolist()


def obtener_datos_filtrados(db, filtro_tiempo, etiquetas_seleccionadas, termino_busqueda):
    """Orquesta los filtros de tiempo, etiquetas y búsqueda a partir de la capa de datos."""
    datos = db.obtener_datos_con_filtros(filtro_tiempo, etiquetas_seleccionadas)
    datos = aplicar_busqueda_sobre_lista(datos, termino_busqueda)
    return datos


def construir_dataframe_para_export(datos):
    """Construye el DataFrame final listo para exportar a CSV."""
    if not datos:
        return None
    return pd.DataFrame(
        datos,
        columns=['ID', 'Tipo', 'Contenido', 'Etiquetas', 'Fecha', 'Favorito']
    )

class DashboardDB(CerebroDB):
    def __init__(self):
        super().__init__()
    
    def borrar_datos_por_ids(self, ids_a_borrar):
        if not ids_a_borrar:
            return 0
            
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            cursor.execute("BEGIN TRANSACTION")
            
            # Primero obtener las rutas de los archivos antes de borrar
            placeholders = ','.join(['?' for _ in ids_a_borrar])
            cursor.execute(f"SELECT id, tipo, contenido FROM datos WHERE id IN ({placeholders})", ids_a_borrar)
            registros_a_borrar = cursor.fetchall()
            
            # Borrar archivos físicos
            archivos_borrados = 0
            archivos_fallidos = 0
            for id, tipo, contenido in registros_a_borrar:
                if tipo in ['foto', 'pdf']:
                    # Separar comentario y ruta si existe el formato "comentario\nArchivo: ruta"
                    if '\nArchivo: ' in contenido:
                        partes = contenido.split('\nArchivo: ', 1)
                        ruta_archivo = partes[1].strip()
                    else:
                        ruta_archivo = contenido
                        
                    # Borrar archivo físico si existe
                    if os.path.exists(ruta_archivo):
                        try:
                            os.remove(ruta_archivo)
                            archivos_borrados += 1
                        except Exception as e:
                            archivos_fallidos += 1
                            print(f"Error borrando archivo {ruta_archivo}: {e}")
            
            # Ahora borrar los registros de la base de datos
            cursor.execute(f"DELETE FROM datos WHERE id IN ({placeholders})", ids_a_borrar)
            conn.commit()

            cantidad_borrada = cursor.rowcount

            # Feedback adicional en la UI sobre archivos asociados
            if archivos_borrados or archivos_fallidos:
                mensaje_archivos = f"Archivos borrados: {archivos_borrados}"
                if archivos_fallidos:
                    mensaje_archivos += f" | Errores al borrar archivos: {archivos_fallidos}"
                st.info(mensaje_archivos)

            return cantidad_borrada

        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            st.error(f"❌ Error crítico al borrar: {str(e)}")
            return 0
        finally:
            try:
                conn.close()
            except Exception:
                pass
    
    def migrar_etiquetas_antiguas(self):
        """Migra etiquetas antiguas a nuevas taxonomía"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            # Migraciones específicas (sin # porque en DB se guardan sin el símbolo)
            cursor.execute("UPDATE datos SET etiqueta = REPLACE(etiqueta, 'News', 'Novedades') WHERE etiqueta LIKE '%News%'")
            cursor.execute("UPDATE datos SET etiqueta = REPLACE(etiqueta, 'UseCase', 'CasosDeUso') WHERE etiqueta LIKE '%UseCase%'")
            cursor.execute("UPDATE datos SET etiqueta = REPLACE(etiqueta, 'Tactica', 'Hacks') WHERE etiqueta LIKE '%Tactica%'")
            
            conn.commit()
            print("✅ Migración de etiquetas completada")
        except Exception as e:
            print(f"❌ Error en migración: {e}")
        finally:
            conn.close()

    def obtener_etiquetas_nivel_3(self):
        """Extrae etiquetas de Nivel 3 dinámicamente (excluye Nivel 1 y 2)"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Etiquetas de Nivel 1 y 2 a excluir
        nivel_1_2 = ['#LaAgencia', '#GreenHouse', '#Tesis', '#Varios', 
                     '#Prompt', '#Novedades', '#Aprender', '#Herramientas', 
                     '#CasosDeUso', '#LabPersonal', '#Hacks']
        
        try:
            cursor.execute("SELECT DISTINCT etiqueta FROM datos WHERE etiqueta != 'SinEtiqueta'")
            todas_etiquetas = cursor.fetchall()
            
            etiquetas_nivel_3 = set()
            for (etiqueta_str,) in todas_etiquetas:
                etiquetas_individuales = [etiqueta.strip() for etiqueta in etiqueta_str.split(',')]
                for etiqueta in etiquetas_individuales:
                    if etiqueta and etiqueta not in nivel_1_2:
                        etiquetas_nivel_3.add(etiqueta)
            
            return sorted(list(etiquetas_nivel_3))
        except Exception as e:
            print(f"Error obteniendo etiquetas Nivel 3: {e}")
            return []
        finally:
            conn.close()
            
    def obtener_top_etiqueta_por_nivel(self, nivel):
        """Obtiene la etiqueta más usada por nivel específico"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT etiqueta FROM datos WHERE etiqueta != 'SinEtiqueta'")
            todas_etiquetas = cursor.fetchall()
            
            nivel_1 = TAXONOMIA['nivel_1']
            nivel_2 = TAXONOMIA['nivel_2']
            
            contador = {}
            
            for (etiqueta_str,) in todas_etiquetas:
                etiquetas_individuales = [etiqueta.strip() for etiqueta in etiqueta_str.split(',')]
                for etiqueta in etiquetas_individuales:
                    etiqueta_limpia = etiqueta.strip().replace('#', '')
                    
                    if not etiqueta_limpia:
                        continue
                    
                    if nivel == 1 and etiqueta_limpia in nivel_1:
                        contador[etiqueta_limpia] = contador.get(etiqueta_limpia, 0) + 1
                    elif nivel == 2 and etiqueta_limpia in nivel_2:
                        contador[etiqueta_limpia] = contador.get(etiqueta_limpia, 0) + 1
                    elif nivel == 3 and etiqueta_limpia not in nivel_1 and etiqueta_limpia not in nivel_2:
                        contador[etiqueta_limpia] = contador.get(etiqueta_limpia, 0) + 1
            
            if contador:
                top_etiqueta = max(contador.items(), key=lambda x: x[1])
                return f"#{top_etiqueta[0]} ({top_etiqueta[1]})"
            return None

    def obtener_todas_las_etiquetas_unicas(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT etiqueta 
            FROM datos 
            WHERE etiqueta IS NOT NULL AND etiqueta != 'SinEtiqueta'
            ORDER BY etiqueta
        """)
        
        etiquetas_brutas = cursor.fetchall()
        conn.close()
        
        etiquetas_unicas = set()
        for etiquetas in etiquetas_brutas:
            etiquetas_individuales = [etiqueta.strip() for etiqueta in etiquetas[0].split(',')]
            etiquetas_unicas.update(etiquetas_individuales)
        
        return sorted(list(etiquetas_unicas))

def mostrar_tarjeta(dato, key_checkbox, db_instance):
    id, tipo, contenido, etiqueta, fecha = dato[:5]
    favorito = dato[5] if len(dato) > 5 else 0
    
    fecha_formateada = datetime.strptime(fecha, '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y %H:%M')
    
    # Separar comentario y ruta para archivos
    if tipo in ['foto', 'pdf'] and 'Archivo: ' in contenido:
        # Soporta tanto "comentario\nArchivo: ruta" como solo "Archivo: ruta"
        partes = contenido.split('Archivo: ', 1)
        comentario = partes[0].replace('\n', ' ').strip()
        ruta_archivo = partes[1].strip()
        if not comentario:
            comentario = None
    else:
        comentario = contenido
        ruta_archivo = contenido
    
    # Mostrar tarjeta con componentes nativos
    with st.container():
        col1, col2, col3 = st.columns([1, 8, 1])
        
        with col1:
            st.write(f"**{tipo.upper()}**")
        
        with col2:
            st.write(fecha_formateada)
            if etiqueta and etiqueta != "SinEtiqueta":
                st.write(f"🏷️ {etiqueta}")
            
            # Mostrar contenido
            if tipo == "link":
                st.write(f"🔗 [{contenido}]({contenido})")
            elif tipo == "foto":
                if comentario and comentario != ruta_archivo:
                    st.write(f"💬 {comentario}")
                
                # Intentar múltiples rutas posibles
                rutas_posibles = [
                    ruta_archivo,
                    os.path.join(os.getcwd(), ruta_archivo),
                    os.path.join(os.getcwd(), "documentos_locales", os.path.basename(ruta_archivo)),
                    os.path.join(os.getcwd(), "documentos_locales", ruta_archivo)
                ]
                
                archivo_encontrado = None
                for ruta in rutas_posibles:
                    if os.path.exists(ruta):
                        archivo_encontrado = ruta
                        break
                
                if archivo_encontrado:
                    st.image(archivo_encontrado, width=300, caption=os.path.basename(archivo_encontrado))
                else:
                    st.error(f"Archivo no encontrado. Rutas probadas:\n" + "\n".join(rutas_posibles))
                    
            elif tipo == "pdf":
                if comentario and comentario != ruta_archivo:
                    st.write(f"💬 {comentario}")
                
                # Intentar múltiples rutas posibles
                rutas_posibles = [
                    ruta_archivo,
                    os.path.join(os.getcwd(), ruta_archivo),
                    os.path.join(os.getcwd(), "documentos_locales", os.path.basename(ruta_archivo)),
                    os.path.join(os.getcwd(), "documentos_locales", ruta_archivo)
                ]
                
                archivo_encontrado = None
                for ruta in rutas_posibles:
                    if os.path.exists(ruta):
                        archivo_encontrado = ruta
                        break
                
                if archivo_encontrado:
                    nombre_archivo = os.path.basename(archivo_encontrado)
                    with open(archivo_encontrado, "rb") as pdf_file:
                        st.download_button("📄 Abrir PDF", data=pdf_file.read(), file_name=nombre_archivo, mime="application/pdf")
                else:
                    st.error(f"Archivo no encontrado. Rutas probadas:\n" + "\n".join(rutas_posibles))
            else:
                st.write(contenido)
        
        with col3:
            col_fav, col_edit = st.columns(2)
            
            with col_fav:
                if st.button("⭐" if favorito == 0 else "🌟", key=f"fav_{id}_{key_checkbox}"):
                    db_instance.toggle_favorito(id)
                    st.rerun()
            
            with col_edit:
                if st.button("✏️", key=f"edit_{id}_{key_checkbox}"):
                    st.session_state[f"editar_{id}"] = True
        
        # Botón Abrir en Carpeta (solo para archivos)
        if tipo in ['foto', 'pdf']:
            # Intentar múltiples rutas posibles para el botón de carpeta
            rutas_posibles = [
                ruta_archivo,
                os.path.join(os.getcwd(), ruta_archivo),
                os.path.join(os.getcwd(), "documentos_locales", os.path.basename(ruta_archivo)),
                os.path.join(os.getcwd(), "documentos_locales", ruta_archivo)
            ]
            
            archivo_encontrado = None
            for ruta in rutas_posibles:
                if os.path.exists(ruta):
                    archivo_encontrado = ruta
                    break
            
            if archivo_encontrado:
                with col2:
                    if st.button("📂 Abrir en Carpeta", key=f"folder_{id}_{key_checkbox}"):
                        try:
                            # Obtener la carpeta del archivo
                            carpeta = os.path.dirname(os.path.abspath(archivo_encontrado))
                            # Abrir explorador de Windows en esa carpeta sin check=True para evitar error
                            subprocess.run(['explorer', carpeta], shell=True)
                        except Exception as e:
                            st.error(f"No se pudo abrir la carpeta. Error: {e}")
                            st.info(f"Intentando abrir: {carpeta}")
    
    # Diálogo de edición
    if st.session_state.get(f"editar_{id}", False):
        with st.expander(f"Editar recurso #{id}", expanded=True):
            nuevo_contenido = st.text_area("Contenido:", value=contenido, height=100, key=f"edit_text_{id}")
            
            col_guardar, col_cancelar = st.columns(2)
            with col_guardar:
                if st.button("Guardar", key=f"save_{id}"):
                    if db_instance.actualizar_contenido(id, nuevo_contenido):
                        st.success("Actualizado")
                        st.session_state[f"editar_{id}"] = False
                        st.rerun()
                    else:
                        st.error("Error")
            
            with col_cancelar:
                if st.button("Cancelar", key=f"cancel_{id}"):
                    st.session_state[f"editar_{id}"] = False
                    st.rerun()
    
    return False

def main():
    db = DashboardDB()
    
    # Inicializar estado
    if 'ids_seleccionados_para_borrar' not in st.session_state:
        st.session_state.ids_seleccionados_para_borrar = []
    if 'mostrar_confirmacion_borrado' not in st.session_state:
        st.session_state.mostrar_confirmacion_borrado = False
    
    # Header simple
    st.title("🧠 Cerebro Local AI")
    st.write("Tu segundo cerebro digital")
    
    stats = db.obtener_estadisticas()
    
    # Métricas principales
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📁 Recursos", stats['total'])
    with col2:
        st.metric("🔗 Enlaces", stats['por_tipo'].get('link', 0))
    with col3:
        st.metric("📝 Notas", stats['por_tipo'].get('texto', 0))
    
    # Podios de taxonomía
    top_nivel_1 = db.obtener_top_etiqueta_por_nivel(1)
    top_nivel_2 = db.obtener_top_etiqueta_por_nivel(2)
    top_nivel_3 = db.obtener_top_etiqueta_por_nivel(3)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🏆 Top Proyecto", top_nivel_1 if top_nivel_1 else "Sin datos")
    with col2:
        st.metric("🎯 Top Acción", top_nivel_2 if top_nivel_2 else "Sin datos")
    with col3:
        st.metric("🛠️ Top Plataforma", top_nivel_3 if top_nivel_3 else "Sin datos")
    
    st.write("---")
    
    # Barra de búsqueda
    busqueda = st.text_input("🔍 Buscar recursos...", placeholder="Escribe para buscar en contenido y etiquetas...")
    
    st.write("---")
    
    # Termómetro de Productividad
    stats_temporales = db.obtener_estadisticas_temporales()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("📈 Recursos hoy", stats_temporales['recursos_hoy'])
    with col2:
        st.metric("📅 Esta semana", stats_temporales['recursos_semana'])
    
    st.write("---")
    
    with st.sidebar:
        st.header("🎛️ Control")
        
        if st.button("🔄 Actualizar", type="primary"):
            st.rerun()
        
        st.write("### ⏰ Período")
        filtro_tiempo = st.selectbox(
            "Filtrar por tiempo:",
            ["Todo", "Hoy", "Esta semana"],
            index=0
        )
        
        st.write("### 🏷️ Etiquetas")
        todas_etiquetas = db.obtener_todas_las_etiquetas_unicas()
        
        if todas_etiquetas:
            etiquetas_seleccionadas = st.multiselect(
                "Filtrar por etiqueta:",
                todas_etiquetas
            )
        else:
            st.info("Sin etiquetas disponibles")
            etiquetas_seleccionadas = []
        
        st.write("---")
        
        # Exportador de Reportes
        st.write("### 📊 Exportar Datos")

        try:
            # Reutilizar la misma lógica de filtros que el resto de la app
            datos_actuales = obtener_datos_filtrados(db, filtro_tiempo, etiquetas_seleccionadas, busqueda)

            df_export = construir_dataframe_para_export(datos_actuales)
            if df_export is not None:
                csv_data = df_export.to_csv(index=False, encoding='utf-8-sig')

                fecha_actual = datetime.now().strftime("%Y_%m_%d")
                nombre_archivo = f"Reporte_Cerebro_AI_{fecha_actual}.csv"

                st.download_button(
                    label="📥 Descargar Reporte CSV",
                    data=csv_data,
                    file_name=nombre_archivo,
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.info("Sin datos para exportar")
        except Exception:
            st.info("Sin datos para exportar")
        
        with st.expander("📖 Taxonomía"):
            st.write("""
            **Nivel 1 (Proyectos):** LaAgencia, GreenHouse, Tesis, Varios
            
            **Nivel 2 (Acciones):** Prompt, Novedades, Aprender, Herramientas, CasosDeUso, LabPersonal, Hacks
            
            **Nivel 3 (Plataformas):** Todas las demás etiquetas
            """)
        
        with st.expander("📚 Diccionario de Etiquetas"):
            st.markdown("### 📋 Categorías Definidas")
            
            # Etiquetas Nivel 1
            st.markdown("### 🏆 Proyectos (Nivel 1)")
            nivel_1 = TAXONOMIA['nivel_1']
            if nivel_1:
                etiquetas_formateadas = ", ".join([f"`{etiqueta}`" for etiqueta in nivel_1])
                st.markdown(f"*{etiquetas_formateadas}*")
                st.caption(f"Total: {len(nivel_1)} categorías")
            else:
                st.info("Sin categorías Nivel 1 guardadas")
            
            # Etiquetas Nivel 2
            st.markdown("### 🎯 Acciones (Nivel 2)")
            nivel_2 = TAXONOMIA['nivel_2']
            if nivel_2:
                etiquetas_formateadas = ", ".join([f"`{etiqueta}`" for etiqueta in nivel_2])
                st.markdown(f"*{etiquetas_formateadas}*")
                st.caption(f"Total: {len(nivel_2)} categorías")
            else:
                st.info("Sin categorías Nivel 2 guardadas")
            
            # Etiquetas Nivel 3 (dinámicas)
            etiquetas_nivel_3 = db.obtener_etiquetas_nivel_3()
            if etiquetas_nivel_3:
                st.markdown("### 🛠️ Plataformas (Nivel 3)")
                etiquetas_formateadas = ", ".join([f"`{etiqueta}`" for etiqueta in etiquetas_nivel_3])
                st.markdown(f"*{etiquetas_formateadas}*")
                st.caption(f"Total: {len(etiquetas_nivel_3)} etiquetas únicas")
            else:
                st.info("No hay etiquetas Nivel 3 guardadas")
    
    # Datos filtrados para visualización principal (reutiliza la misma lógica)
    datos_filtrados = obtener_datos_filtrados(db, filtro_tiempo, etiquetas_seleccionadas, busqueda)
    
    st.markdown("### 📊 Recursos")
    
    # Feedback visual si no hay resultados
    if busqueda and busqueda.strip() and not datos_filtrados:
        st.info("No se encontraron recursos con esa palabra.")
    else:
        tab1, tab2, tab3 = st.tabs(["📋 Tabla", "🎴 Galería", "⭐ Destacados"])
        
        # Filtrar destacados para la tercera pestaña
        datos_destacados = [dato for dato in datos_filtrados if len(dato) > 5 and dato[5] == 1]
        
        with tab1:
            if datos_filtrados:
                df = pd.DataFrame(
                    datos_filtrados,
                    columns=['ID', 'Tipo', 'Contenido', 'Etiquetas', 'Fecha', 'Favorito']
                )
                df['Fecha'] = pd.to_datetime(df['Fecha']).dt.strftime('%d/%m/%Y %H:%M')
                df['Seleccionar'] = False
                df['Favorito'] = df['Favorito'].apply(lambda x: '⭐' if x == 1 else '○')

                edited_df = st.data_editor(
                    df,
                    hide_index=True,
                    column_config={
                        "Seleccionar": st.column_config.CheckboxColumn(
                            "Seleccionar",
                            help="Marca para eliminar este recurso",
                            default=False,
                        )
                    }
                )

                seleccionados = edited_df[edited_df['Seleccionar'] == True]
                tiene_seleccionados = not seleccionados.empty
            else:
                st.info("📭 Sin datos para mostrar")
                tiene_seleccionados = False
            
            if tiene_seleccionados:
                st.write("---")
                if st.button("🗑️ Eliminar seleccionados"):
                    ids_seleccionados = seleccionados['ID'].tolist()
                    st.session_state.ids_seleccionados_para_borrar = ids_seleccionados
                    st.session_state.mostrar_confirmacion_borrado = True
                    st.rerun()
            
            if 'mostrar_confirmacion_borrado' in st.session_state and st.session_state.mostrar_confirmacion_borrado:
                if 'ids_seleccionados_para_borrar' in st.session_state and st.session_state.ids_seleccionados_para_borrar:
                    st.warning(f"⚠️ ¿Eliminar {len(st.session_state.ids_seleccionados_para_borrar)} elementos?")
                    col_confirm, col_cancel = st.columns(2)
                    
                    with col_confirm:
                        if st.button("✅ Confirmar", type="primary"):
                            cantidad_borrada = db.borrar_datos_por_ids(st.session_state.ids_seleccionados_para_borrar)
                            
                            if cantidad_borrada > 0:
                                st.success(f"✅ {cantidad_borrada} elementos eliminados")
                                st.session_state.ids_seleccionados_para_borrar = []
                                st.session_state.mostrar_confirmacion_borrado = False
                                st.rerun()
                            else:
                                st.error("❌ No se pudieron eliminar")
                                st.session_state.mostrar_confirmacion_borrado = False
                    
                    with col_cancel:
                        if st.button("❌ Cancelar"):
                            st.info("Operación cancelada")
                            st.session_state.ids_seleccionados_para_borrar = []
                            st.session_state.mostrar_confirmacion_borrado = False
            else:
                st.info("📭 Sin datos para mostrar")
    
        with tab2:
            if datos_filtrados:
                for dato in datos_filtrados:
                    mostrar_tarjeta(dato, "galeria", db)
            else:
                st.info("📭 Sin datos para mostrar")
    
        with tab3:
            if datos_destacados:
                for dato in datos_destacados:
                    mostrar_tarjeta(dato, "destacados", db)
            else:
                st.info("📭 Sin recursos destacados")
    
    st.markdown("---")
    st.markdown("*Cerebro Local AI • Tu segundo cerebro digital*")

if __name__ == "__main__":
    main()
