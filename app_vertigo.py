import streamlit as st
import json
import requests
from datetime import datetime
from groq import Groq

# --- LAS LLAVES DE LA NUBE ---
MI_LLAVE_GROQ = st.secrets["MI_LLAVE_GROQ"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

cliente_groq = Groq(api_key=MI_LLAVE_GROQ)

# Cabeceras universales para hablar con Supabase directamente (Vía REST)
headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates"
}

st.set_page_config(page_title="Proyecto Vértigo", page_icon="🚀")
st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    .stChatMessage { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 15px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 2. SISTEMA DE MEMORIA EN LA NUBE
if "chat_actual" not in st.session_state:
    st.session_state.chat_actual = datetime.now().strftime("Chat_%Y%m%d_%H%M%S")
    st.session_state.messages = []
    st.session_state.rol = "Socio Estratégico" 

def guardar_memoria():
    datos = {
        "id": st.session_state.chat_actual,
        "rol": st.session_state.rol,
        "mensajes": st.session_state.messages
    }
    # Limpiamos la URL por si tiene una diagonal extra al final
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chats"
    
    try:
        respuesta = requests.post(url, headers=headers, json=datos)
        # Si Supabase rechaza el guardado, nos mostrará una alerta en la app
        if respuesta.status_code not in [200, 201, 204]:
            st.error(f"🚨 Error de Supabase al guardar: {respuesta.text} (Revisa si apagaste el RLS en la tabla)")
    except Exception as e:
        st.error(f"🚨 Error de conexión: {e}")

# 3. EL ARCHIVERO (Conectado a Supabase vía REST)
with st.sidebar:
    st.title("🗄️ El Archivero")
    if st.button("➕ Crear Nuevo Chat", use_container_width=True):
        st.session_state.chat_actual = datetime.now().strftime("Chat_%Y%m%d_%H%M%S")
        st.session_state.messages = []
        st.session_state.rol = "Socio Estratégico"
        st.rerun()
        
    st.markdown("---")
    st.subheader("Chats Guardados")
    
    try:
        url_get = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chats?select=id,rol"
        respuesta_get = requests.get(url_get, headers=headers)
        
        if respuesta_get.status_code == 200:
            archivos = respuesta_get.json()
            archivos.sort(key=lambda x: x["id"], reverse=True)
            
            for archivo in archivos:
                id_chat = archivo["id"]
                nombre_rol = archivo.get("rol", "Chat")
                
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    if st.button(f"🎭 {nombre_rol}", key=f"load_{id_chat}", use_container_width=True):
                        url_chat = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chats?id=eq.{id_chat}&select=*"
                        resp_chat = requests.get(url_chat, headers=headers)
                        if resp_chat.status_code == 200 and len(resp_chat.json()) > 0:
                            chat_data = resp_chat.json()[0]
                            st.session_state.chat_actual = id_chat
                            st.session_state.rol = chat_data.get("rol", "Socio Estratégico")
                            st.session_state.messages = chat_data.get("mensajes", [])
                        st.rerun()
                
                with col2:
                    if st.button("❌", key=f"del_{id_chat}"):
                        url_del = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chats?id=eq.{id_chat}"
                        requests.delete(url_del, headers=headers)
                        if st.session_state.chat_actual == id_chat:
                            st.session_state.chat_actual = datetime.now().strftime("Chat_%Y%m%d_%H%M%S")
                            st.session_state.messages = []
                            st.session_state.rol = "Socio Estratégico"
                        st.rerun()
        else:
            st.sidebar.warning("Aún no hay chats guardados o el RLS está bloqueando la lectura.")
    except Exception as e:
        st.sidebar.error("Error conectando a la base de datos.")

st.title("¿En qué te puedo ayudar hoy? 🌌")
st.caption(f"🛡️ Proyecto Vértigo | Nube: {st.session_state.chat_actual}")

if "rol" not in st.session_state:
    st.session_state.rol = "Socio Estratégico"

st.session_state.rol = st.text_input("🎭 Define quién es Vértigo en esta sesión específica:", value=st.session_state.rol)

SYSTEM_PROMPT = f"""
Actúa y responde asumiendo este rol: {st.session_state.rol}.
Eres Vértigo, pero adaptado 100% a ese papel. 
Hablas de forma natural, directa y empática. Nunca digas 'Como inteligencia artificial...'. Sé el personaje.
"""

for message in st.session_state.messages:
    icono = "👤" if message["role"] == "user" else "✨"
    with st.chat_message(message["role"], avatar=icono):
        st.markdown(message["content"])

# 5. EL CHAT PRINCIPAL (Motor y Memoria en Nube)
if prompt := st.chat_input("Escribe tu mensaje..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="✨"):
        with st.spinner("Procesando en la nube..."):
            mensajes_completos = [{'role': 'system', 'content': SYSTEM_PROMPT}] + st.session_state.messages
            
            respuesta_nube = cliente_groq.chat.completions.create(
                messages=mensajes_completos,
                model="llama-3.1-8b-instant", 
            )
            
            full_response = respuesta_nube.choices[0].message.content
            st.markdown(full_response)
            
    st.session_state.messages.append({"role": "assistant", "content": full_response})
    guardar_memoria()