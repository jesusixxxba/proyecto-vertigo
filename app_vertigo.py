import streamlit as st
import json
import requests
import re
from datetime import datetime
from groq import Groq

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

# Estética IxInteractive
st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    .stChatMessage { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 15px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

def es_correo_valido(correo):
    patron = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(patron, correo) is not None

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
                st.error("🚨 Ingresa un correo válido.")
    st.stop()

# Inicializar sesión de chat
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
# 2. EL ARCHIVERO (BANDEJA DE CHATS REPARADA)
# ==========================================
with st.sidebar:
    st.title("👤 Mi Perfil")
    st.caption(f"Usuario: **{st.session_state.usuario_id}**")
    
    col_n, col_s = st.columns(2)
    with col_n:
        if st.button("➕ Nuevo", use_container_width=True):
            st.session_state.chat_actual = datetime.now().strftime("Chat_%Y%m%d_%H%M%S")
            st.session_state.messages = []
            st.rerun()
    with col_s:
        if st.button("🚪 Salir", use_container_width=True):
            st.session_state.clear()
            st.rerun()
            
    st.markdown("---")
    st.subheader("📂 Tus Chats Guardados")
    
    # Lógica para recuperar el historial de este usuario
    try:
        url_get = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chats"
        parametros_get = {"usuario_id": f"eq.{st.session_state.usuario_id}", "select": "id,mensajes"}
        respuesta_get = requests.get(url_get, headers=headers, params=parametros_get)
        
        if respuesta_get.status_code == 200:
            archivos = respuesta_get.json()
            # Ordenar por fecha (ID) de más reciente a más antiguo
            archivos.sort(key=lambda x: x["id"], reverse=True)
            
            for archivo in archivos:
                id_chat = archivo["id"]
                nombre_limpio = id_chat.replace("Chat_", "").replace("_", " ")
                
                col_btn, col_del = st.columns([4, 1])
                with col_btn:
                    if st.button(f"💬 {nombre_limpio[:14]}", key=f"L_{id_chat}", use_container_width=True):
                        st.session_state.chat_actual = id_chat
                        st.session_state.messages = archivo.get("mensajes", [])
                        st.rerun()
                with col_del:
                    if st.button("🗑️", key=f"D_{id_chat}"):
                        requests.delete(url_get, headers=headers, params={"id": f"eq.{id_chat}"})
                        st.rerun()
    except:
        st.sidebar.error("Error al cargar historial.")

# ==========================================
# 3. INTERFAZ DE CHAT
# ==========================================
st.title("Hola, soy Maya 🌌")
st.caption(f"Sesión: {st.session_state.chat_actual}")

SYSTEM_PROMPT = "Eres Maya, una IA femenina, profesional y cálida de IxInteractive Studios."

# Mostrar historial
for msg in st.session_state.messages:
    avatar = "👤" if msg["role"] == "user" else "🌌"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# Entrada
if prompt := st.chat_input("Escribe tu mensaje para Maya..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🌌"):
        with st.spinner("Maya pensando..."):
            historial = [{'role': 'system', 'content': SYSTEM_PROMPT}] + st.session_state.messages
            
            res = cliente_groq.chat.completions.create(
                messages=historial,
                model="llama-3.3-70b-versatile", 
            )
            
            full_response = res.choices[0].message.content
            st.markdown(full_response)
            
    st.session_state.messages.append({"role": "assistant", "content": full_response})
    guardar_memoria()