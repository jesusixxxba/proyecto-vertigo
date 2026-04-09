import streamlit as st
import json
import requests
import re
from datetime import datetime
from openai import OpenAI # <--- NUEVA LIBRERÍA

# --- LAS LLAVES DE LA NUBE ---
MI_LLAVE_GEMINI = st.secrets["MI_LLAVE_GEMINI"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

# Conectamos la librería directamente a los servidores de Google Gemini
cliente_ia = OpenAI(
    api_key=MI_LLAVE_GEMINI, 
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

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

def es_correo_valido(correo):
    patron = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(patron, correo) is not None

# 1. SISTEMA DE ACCESO
if "usuario_id" not in st.session_state:
    st.title("🏢 IxInteractive Studios")
    st.subheader("Acceso a Maya AI")
    st.markdown("Por favor, ingresa tu correo electrónico corporativo o personal para acceder a tu entorno de trabajo.")
    
    with st.form("login_form"):
        correo_input = st.text_input("✉️ Correo electrónico:", placeholder="ejemplo@correo.com")
        submit_button = st.form_submit_button("Iniciar Sesión", use_container_width=True)
        
        if submit_button:
            correo_limpio = correo_input.strip().lower()
            if es_correo_valido(correo_limpio):
                st.session_state.usuario_id = correo_limpio
                st.rerun()
            else:
                st.error("🚨 Acceso denegado: Por favor, ingresa un correo electrónico válido.")
                
    st.stop()

# 2. SISTEMA DE MEMORIA EN LA NUBE
if "chat_actual" not in st.session_state:
    st.session_state.chat_actual = datetime.now().strftime("Chat_%Y%m%d_%H%M%S")
    st.session_state.messages = []
    st.session_state.rol = "Maya AI" 

def guardar_memoria():
    datos = {
        "id": st.session_state.chat_actual,
        "rol": st.session_state.rol,
        "mensajes": st.session_state.messages,
        "usuario_id": st.session_state.usuario_id 
    }
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chats"
    try:
        requests.post(url, headers=headers, json=datos)
    except Exception as e:
        st.error(f"🚨 Error de conexión: {e}")

# 3. EL ARCHIVERO
with st.sidebar:
    st.title("👤 Mi Perfil")
    st.caption(f"Conectado como:\n**{st.session_state.usuario_id}**")
    
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.clear()
        st.rerun()
        
    st.markdown("---")
    
    if st.button("➕ Nueva Conversación", use_container_width=True):
        st.session_state.chat_actual = datetime.now().strftime("Chat_%Y%m%d_%H%M%S")
        st.session_state.messages = []
        st.rerun()
        
    st.markdown("---")
    st.subheader("Tus Chats Privados")
    
    try:
        url_get = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chats"
        parametros_get = {"usuario_id": f"eq.{st.session_state.usuario_id}", "select": "id,rol"}
        respuesta_get = requests.get(url_get, headers=headers, params=parametros_get)
        
        if respuesta_get.status_code == 200:
            archivos = respuesta_get.json()
            archivos.sort(key=lambda x: x["id"], reverse=True)
            
            for archivo in archivos:
                id_chat = archivo["id"]
                fecha_limpia = id_chat.replace("Chat_", "").replace("_", " a las ")
                nombre_visual = f"Sesión {fecha_limpia[:15]}"
                
                col1, col2 = st.columns([4, 1])
                with col1:
                    if st.button(f"💬 {nombre_visual}", key=f"load_{id_chat}", use_container_width=True):
                        parametros_chat = {"id": f"eq.{id_chat}", "select": "*"}
                        resp_chat = requests.get(url_get, headers=headers, params=parametros_chat)
                        if resp_chat.status_code == 200 and len(resp_chat.json()) > 0:
                            chat_data = resp_chat.json()[0]
                            st.session_state.chat_actual = id_chat
                            st.session_state.messages = chat_data.get("mensajes", [])
                        st.rerun()
                with col2:
                    if st.button("❌", key=f"del_{id_chat}"):
                        parametros_del = {"id": f"eq.{id_chat}"}
                        requests.delete(url_get, headers=headers, params=parametros_del)
                        if st.session_state.chat_actual == id_chat:
                            st.session_state.chat_actual = datetime.now().strftime("Chat_%Y%m%d_%H%M%S")
                            st.session_state.messages = []
                        st.rerun()
    except Exception as e:
        pass

# 4. LA INTERFAZ PRINCIPAL
st.title("Hola, soy Maya. ¿En qué te ayudo hoy? 🌌")
st.caption(f"🛡️ IxInteractive Studios | ID: {st.session_state.chat_actual}")

SYSTEM_PROMPT = """
Eres Maya, una inteligencia artificial avanzada, sumamente inteligente y adaptable.
Tienes una personalidad femenina, profesional, cálida y empática. 
Debes adaptar el nivel de tus respuestas según la persona que te hable, pero siempre mantén un tono resolutivo y claro.

REGLA ESTRICTA DE IDENTIDAD: 
No menciones quién te creó a menos que el usuario te pregunte explícitamente "¿Quién te creó?", "¿Quién es tu creador?" o algo similar. 
Solo cuando te pregunten directamente, responde con orgullo que fuiste desarrollada por "IxInteractive Studios". Bajo ninguna circunstancia menciones el nombre Jesús ni Ixba.

Nunca digas "Como inteligencia artificial...", simplemente sé tú misma.
"""

for message in st.session_state.messages:
    icono = "👤" if message["role"] == "user" else "🌌"
    with st.chat_message(message["role"], avatar=icono):
        st.markdown(message["content"])

if prompt := st.chat_input("Escribe tu mensaje para Maya..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🌌"):
        with st.spinner("Maya está analizando..."):
            mensajes_completos = [{'role': 'system', 'content': SYSTEM_PROMPT}] + st.session_state.messages
            
            # ¡EL NUEVO MOTOR GOOGLE GEMINI PRO!
            respuesta_nube = cliente_ia.chat.completions.create(
                messages=mensajes_completos,
                model="gemini-2.5-pro"
            )
            
            full_response = respuesta_nube.choices[0].message.content
            st.markdown(full_response)
            
    st.session_state.messages.append({"role": "assistant", "content": full_response})
    guardar_memoria()