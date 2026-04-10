import streamlit as st
import json
import requests
import re
from datetime import datetime
from groq import Groq

# ===================== 1. CONFIGURACIÓN Y LLAVES =====================
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

st.set_page_config(page_title="Maya | IxInteractive", page_icon="🌌", layout="centered")

# Estética Profesional IxInteractive
st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    .stChatMessage { background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-bottom: 10px; }
    .main-header { font-size: 2.5rem; font-weight: 700; color: #a5d6ff; text-align: center; margin-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

# Validación de Correo
def es_correo_valido(correo):
    patron = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(patron, correo) is not None

# ===================== 2. SISTEMA DE ACCESO =====================
if "usuario_id" not in st.session_state:
    st.markdown('<h1 class="main-header">IxInteractive Studios</h1>', unsafe_allow_html=True)
    st.subheader("Acceso a Maya AI")
    
    with st.form("login_form"):
        correo_input = st.text_input("✉️ Correo electrónico:", placeholder="tu@correo.com")
        if st.form_submit_button("Iniciar Sesión", use_container_width=True):
            correo_limpio = correo_input.strip().lower()
            if es_correo_valido(correo_limpio):
                st.session_state.usuario_id = correo_limpio
                st.rerun()
            else:
                st.error("🚨 Por favor, ingresa un correo válido.")
    st.stop()

# Inicialización de sesión
if "chat_actual" not in st.session_state:
    st.session_state.chat_actual = datetime.now().strftime("Chat_%Y%m%d_%H%M%S")
    st.session_state.messages = []

def guardar_memoria():
    """Sincroniza el chat con las columnas 'id', 'rol' y 'mensajes' de Supabase."""
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chats"
    datos = {
        "id": st.session_state.chat_actual,
        "rol": st.session_state.usuario_id,  # Mapeado a tu columna 'rol' en Supabase
        "mensajes": st.session_state.messages
    }
    try:
        requests.post(url, headers=headers, json=datos)
    except:
        pass

# ===================== 3. SIDEBAR (HISTORIAL DE CHATS) =====================
with st.sidebar:
    st.title("👤 Mi Perfil")
    st.caption(f"Conectado: **{st.session_state.usuario_id}**")
    
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
    st.subheader("📂 Chats Guardados")
    
    try:
        url_get = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chats"
        params = {
            "rol": f"eq.{st.session_state.usuario_id}", 
            "select": "id,mensajes",
            "order": "id.desc"
        }
        res_db = requests.get(url_get, headers=headers, params=params)
        
        if res_db.status_code == 200:
            chats = res_db.json()
            for chat in chats:
                id_c = chat["id"]
                label = id_c.replace("Chat_", "").replace("_", " ")
                
                c_btn, c_del = st.columns([4, 1])
                with c_btn:
                    if st.button(f"💬 {label[:14]}", key=f"L_{id_c}", use_container_width=True):
                        st.session_state.chat_actual = id_c
                        st.session_state.messages = chat.get("mensajes", [])
                        st.rerun()
                with c_del:
                    if st.button("🗑️", key=f"D_{id_c}"):
                        requests.delete(url_get, headers=headers, params={"id": f"eq.{id_c}"})
                        st.rerun()
    except:
        st.caption("Conectando con historial...")

# ===================== 4. INTERFAZ DE CHAT =====================
st.title("Hola, soy Maya 🌌")
st.caption(f"🛡️ IxInteractive Studios | ID: {st.session_state.chat_actual}")

SYSTEM_PROMPT = """
Eres Maya, una inteligencia artificial avanzada de IxInteractive Studios. 
Eres femenina, profesional, cálida y sumamente inteligente. 
Tu objetivo es ser la base de un ecosistema de aplicaciones innovadoras.
"""

for msg in st.session_state.messages:
    avatar = "👤" if msg["role"] == "user" else "🌌"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

if prompt := st.chat_input("Escribe tu mensaje..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🌌"):
        with st.spinner("Maya está pensando..."):
            historial = [{'role': 'system', 'content': SYSTEM_PROMPT}] + st.session_state.messages
            
            try:
                res = cliente_groq.chat.completions.create(
                    messages=historial,
                    model="llama-3.3-70b-versatile",
                    temperature=0.75,
                    max_tokens=1200
                )
                
                full_response = res.choices[0].message.content
                st.markdown(full_response)
                
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                guardar_memoria()
                st.rerun()
                
            except Exception as e:
                st.error(f"🚨 Error de motor: {str(e)}")