"""
Blackboard Personal - App minimalista en Streamlit
====================================================
Organiza pendientes de Universidad, Trabajo y Día a día en una sola
página, con persistencia en un archivo JSON local.

Cómo correrla localmente:
    streamlit run blackboard_app.py

Cómo desplegarla en Streamlit Cloud:
    1. Sube este archivo (y requirements.txt) a un repo de GitHub.
    2. En share.streamlit.io, conecta el repo y selecciona este archivo.
    3. Streamlit Cloud instala automáticamente lo que esté en requirements.txt.

requirements.txt necesario:
    streamlit
"""

import json
import os
from datetime import datetime, date

import streamlit as st

# ---------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE PERSISTENCIA
# ---------------------------------------------------------------------------
# Usamos un archivo JSON como "base de datos" simple. Es legible, fácil de
# depurar y suficiente para una app personal de uso ligero.
#
# IMPORTANTE sobre Streamlit Cloud: el sistema de archivos ahí es EFÍMERO.
# Si la app se reinicia (por inactividad o un nuevo deploy), este archivo
# se borra. Para uso personal esto suele ser aceptable, pero si quieres
# persistencia garantizada a largo plazo, el siguiente paso sería usar
# algo como Google Sheets, Supabase o SQLite + un volumen externo.
DATA_FILE = "blackboard_data.json"

# Estructura por defecto de los datos. Cada categoría es una lista de
# diccionarios (tareas/notas), para que sea fácil agregar campos luego.
DEFAULT_DATA = {
    "universidad": [],
    "trabajo": [],
    "dia_a_dia": [],
}


def cargar_datos() -> dict:
    """Lee el archivo JSON. Si no existe, lo crea con la estructura vacía."""
    if not os.path.exists(DATA_FILE):
        guardar_datos(DEFAULT_DATA)
        return DEFAULT_DATA.copy()

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_datos(data: dict) -> None:
    """Escribe el diccionario completo de vuelta al archivo JSON."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 2. ESTADO DE LA APP (session_state)
# ---------------------------------------------------------------------------
# st.session_state es la "memoria" de Streamlit mientras el navegador sigue
# abierto. Cada vez que el usuario interactúa, Streamlit vuelve a correr
# TODO el script de arriba a abajo, así que sin session_state perderíamos
# el estado entre clics. Aquí cargamos los datos del JSON SOLO una vez,
# al inicio de la sesión, y luego trabajamos sobre esa copia en memoria.
if "data" not in st.session_state:
    st.session_state.data = cargar_datos()


def agregar_item(categoria: str, texto: str, con_fecha: bool = False, fecha=None):
    """Agrega un nuevo pendiente/nota a una categoría y guarda en disco."""
    if not texto.strip():
        return  # Evita guardar entradas vacías

    item = {
        "texto": texto.strip(),
        "hecho": False,
        "creado": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "fecha_entrega": fecha.strftime("%Y-%m-%d") if con_fecha and fecha else None,
    }
    st.session_state.data[categoria].append(item)
    guardar_datos(st.session_state.data)


def eliminar_item(categoria: str, index: int):
    """Elimina un item por su posición en la lista."""
    st.session_state.data[categoria].pop(index)
    guardar_datos(st.session_state.data)


def toggle_item(categoria: str, index: int):
    """Marca/desmarca un item como hecho."""
    st.session_state.data[categoria][index]["hecho"] = not st.session_state.data[categoria][index]["hecho"]
    guardar_datos(st.session_state.data)


# ---------------------------------------------------------------------------
# 3. FUNCIÓN REUTILIZABLE PARA RENDERIZAR UNA LISTA DE PENDIENTES
# ---------------------------------------------------------------------------
# En vez de repetir el mismo código en cada pestaña, creamos una función
# genérica que recibe la categoría y dibuja: el formulario para agregar,
# y la lista de items existentes con checkbox + botón de borrar.
def render_lista(categoria: str, placeholder: str, con_fecha: bool = False):
    # --- Formulario para agregar un nuevo item ---
    # st.form agrupa inputs para que la app no se refresque con cada letra
    # tecleada, solo al presionar "Agregar".
    with st.form(key=f"form_{categoria}", clear_on_submit=True):
        col1, col2 = st.columns([3, 1]) if con_fecha else (st.columns([1])[0], None)

        if con_fecha:
            texto = col1.text_input("Nuevo pendiente", placeholder=placeholder, label_visibility="collapsed")
            fecha = col2.date_input("Fecha de entrega", value=date.today(), label_visibility="collapsed")
        else:
            texto = col1.text_input("Nueva nota", placeholder=placeholder, label_visibility="collapsed")
            fecha = None

        enviado = st.form_submit_button("➕ Agregar", use_container_width=True)
        if enviado:
            agregar_item(categoria, texto, con_fecha, fecha)
            st.rerun()  # Refresca la app para mostrar el nuevo item al instante

    st.divider()

    # --- Lista de items existentes ---
    items = st.session_state.data[categoria]

    if not items:
        st.caption("No hay nada por aquí todavía ✨")
        return

    # Ordenamos: los no hechos primero, y entre ellos por fecha de entrega
    # (los que no tienen fecha van al final).
    items_con_index = list(enumerate(items))
    items_con_index.sort(key=lambda par: (par[1]["hecho"], par[1]["fecha_entrega"] or "9999"))

    for idx, item in items_con_index:
        c1, c2, c3 = st.columns([0.1, 0.75, 0.15])

        # Checkbox para marcar como hecho
        hecho = c1.checkbox("", value=item["hecho"], key=f"chk_{categoria}_{idx}")
        if hecho != item["hecho"]:
            toggle_item(categoria, idx)
            st.rerun()

        # Texto del item (tachado si ya está hecho)
        texto_mostrado = item["texto"]
        if item["fecha_entrega"]:
            texto_mostrado += f"  📅 `{item['fecha_entrega']}`"
        if item["hecho"]:
            c2.markdown(f"~~{texto_mostrado}~~")
        else:
            c2.markdown(texto_mostrado)

        # Botón para eliminar
        if c3.button("🗑️", key=f"del_{categoria}_{idx}"):
            eliminar_item(categoria, idx)
            st.rerun()


# ---------------------------------------------------------------------------
# 4. CONFIGURACIÓN DE LA PÁGINA Y LAYOUT PRINCIPAL
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Mi Blackboard",
    page_icon="📌",
    layout="centered",  # "centered" se ve mejor en iPhone que "wide"
)

st.title("📌 Mi Blackboard")

# st.tabs crea pestañas; cada "with tab:" define qué va dentro de cada una.
tab_uni, tab_trabajo, tab_dia = st.tabs(["🎓 Universidad", "💼 Trabajo", "📝 Día a día"])

with tab_uni:
    st.subheader("Pendientes y entregas")
    render_lista("universidad", "Ej: Entregar informe de Cálculo", con_fecha=True)

with tab_trabajo:
    st.subheader("Horario: martes a viernes, 9:00 am – 2:30 pm")
    st.caption("Notas rápidas para durante tu jornada laboral.")
    render_lista("trabajo", "Ej: Llamar al proveedor antes de las 11am", con_fecha=False)

with tab_dia:
    st.subheader("Apuntes y recordatorios personales")
    render_lista("dia_a_dia", "Ej: Comprar pan al salir", con_fecha=False)

# ---------------------------------------------------------------------------
# 5. NOTA FINAL (sidebar con info útil)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ℹ️ Acerca de esta app")
    st.caption(
        "Los datos se guardan en `blackboard_data.json`, en el mismo "
        "directorio que la app. En Streamlit Cloud, recuerda que el "
        "almacenamiento es temporal: si la app se reinicia, se pierde."
    )
