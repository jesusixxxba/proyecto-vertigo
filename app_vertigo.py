import streamlit as st
import json
import requests
import re
from datetime import datetime
from groq import Groq
from PIL import Image # <--- NUEVO: Para procesar imágenes
import io
import base64

# --- LAS LLAVES DE LA NUBE ---
MI_LLAVE_GROQ = st.secrets["MI_LLAVE_GROQ"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

cliente_groq = Groq(api_key=MI_LLAVE_GROQ)

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates"
}

st.set_page_config(page_title="Maya | IxInteractive", page_icon="🌌")
st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    .stChatMessage { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 15px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 0. FUNCIONES DE APOYO
# ==========================================
def es_correo_valido(correo):
    patron = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(patron, correo) is not None

def procesar_imagen_a_base64(archivo_subido):
    # Convierte la imagen subida a un formato que la IA pueda leer
    img = Image.open(archivo_subido)
    buffered = io.BytesIO()
    # Forzamos a JPEG para que sea más ligero
    img.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

# ==========================================
# 1. SISTEMA DE ACCESO
# ==========================================
if "usuario_id" not in st.session_state:
    st.title("🏢 IxInteractive Studios")
    st.subheader("Acceso a Maya AI")
    
    with st.form("login_form"):
        correo_input = st.text_input("✉️ Correo electrónico:", placeholder="tu@correo.com")
        submit_button = st.form_submit_button("Iniciar Sesión", use_container_width=True)
        
        if submit_button:
            correo_limpio = correo_input.strip().lower()
            if es_correo_valido(correo_limpio):
                st.session_state.usuario_id = correo_limpio
                st.rerun()
            else:
                st.error("🚨 Acceso denegado: Ingresa un correo válido.")
    st.stop()

# ==========================================
# 2. MEMORIA
# ==========================================
if "chat_actual" not in st.session_state:
    st.session_state.chat_actual = datetime.now().strftime("Chat_%Y%m%d_%H%M%S")
    st.session_state.messages = []

def guardar_memoria():
    datos = {
        "id": st.session_state.chat_actual,
        "mensajes": st.session_state.messages,
        "usuario_id": st.session_state.usuario_id 
    }
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chats"
    try:
        requests.post(url, headers=headers, json=datos)
    except:
        pass

# ==========================================
# 3. BARRA LATERAL (ARCHIVERO)
# ==========================================
with st.sidebar:
    st.title("👤 Mi Perfil")
    st.caption(f"Usuario: **{st.session_state.usuario_id}**")
    
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.clear()
        st.rerun()
        
    st.markdown("---")
    if st.button("➕ Nuevo Chat", use_container_width=True):
        st.session_state.chat_actual = datetime.now().strftime("Chat_%Y%m%d_%H%M%S")
        st.session_state.messages = []
        st.rerun()
        
    st.markdown("---")
    st.subheader("Chats Guardados")
    
    try:
        url_get = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chats"
        params = {"usuario_id": f"eq.{st.session_state.usuario_id}", "select": "id"}
        resp = requests.get(url_get, headers=headers, params=params)
        
        if resp.status_code == 200:
            chats = resp.json()
            chats.sort(key=lambda x: x["id"], reverse=True)
            for chat in chats:
                if st.button(f"💬 {chat['id'][:15]}", key=chat['id'], use_container_width=True):
                    p_chat = {"id": f"eq.{chat['id']}", "select": "*"}
                    r_chat = requests.get(url_get, headers=headers, params=p_chat)
                    if r_chat.status_code == 200 and r_chat.json():
                        st.session_state.chat_actual = chat['id']
                        st.session_state.messages = r_chat.json()[0].get("mensajes", [])
                        st.rerun()
    except: pass

# ==========================================
# 4. INTERFAZ PRINCIPAL CON "OJOS"
# ==========================================
st.title("Hola, soy Maya 🌌")
st.caption(f"🛡️ IxInteractive Studios | ID: {st.session_state.chat_actual}")

SYSTEM_PROMPT = """Eres Maya, una IA femenina, profesional y cálida de IxInteractive Studios. 
Tienes la capacidad de ver imágenes y analizarlas con detalle. Mantén siempre un tono resolutivo."""

# Mostrar historial (con soporte para imágenes)
for msg in st.session_state.messages:
    icono = "👤" if msg["role"] == "user" else "🌌"
    with st.chat_message(msg["role"], avatar=icono):
        st.markdown(msg["content"])
        if "image" in msg and msg["image"]:
            st.image(msg["image"], width=300)

# Input del chat con botón de "Cámara" (accept_file=True)
if prompt := st.chat_input("Escribe o sube una imagen para Maya...", accept_file=True, file_type=["jpg", "jpeg", "png"]):
    
    img_b64 = None
    # Si el usuario subió una imagen
    if prompt.files:
        img_b64 = procesar_imagen_a_base64(prompt.files[0])
    
    # Guardar el mensaje del usuario
    st.session_state.messages.append({
        "role": "user", 
        "content": prompt.text, 
        "image": f"data:image/jpeg;base64,{img_b64}" if img_b64 else None
    })
    
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt.text)
        if img_b64:
            st.image(prompt.files[0], width=300)

    # Respuesta de Maya
    with st.chat_message("assistant", avatar="🌌"):
        with st.spinner("Maya está observando..."):
            # Construir el formato especial para visión
            mensajes_api = [{"role": "system", "content": SYSTEM_PROMPT}]
            
            for m in st.session_state.messages:
                if m.get("image"):
                    contenido = [
                        {"type": "text", "text": m["content"] or "Analiza esta imagen"},
                        {"type": "image_url", "image_url": {"url": m["image"]}}
                    ]
                else:
                    contenido = m["content"]
                mensajes_api.append({"role": m["role"], "content": contenido})

            try:
                # Usamos el modelo de visión de Groq
                respuesta = cliente_groq.chat.completions.create(
                    messages=mensajes_api,
                    model="moonshotai/kimi-k2-instruct-0905"
                )
                full_response = respuesta.choices[0].message.content
                st.markdown(full_response)
                
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                guardar_memoria()
            except Exception as e:
                st.error(f"🚨 Error de motor: {e}")