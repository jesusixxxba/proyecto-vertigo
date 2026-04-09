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

st.set_page_config(page_title="Proyecto Maya", page_icon="🌌")
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
    st.session_state.rol = "Maya AI" # Se mantiene por compatibilidad con la base de datos vieja

def guardar_memoria():
    datos = {
        "id": st.session_state.chat_actual,
        "rol": st.session_state.rol,
        "mensajes": st.session_state.messages
    }
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chats"
    try:
        respuesta = requests.post(url, headers=headers, json=datos)
        if respuesta.status_code not in [200, 201, 204]:
            st.error(f"🚨 Error de Supabase al guardar: {respuesta.text}")
    except Exception as e:
        st.error(f"🚨 Error de conexión: {e}")

# 3. EL ARCHIVERO
with st.sidebar:
    st.title("🗄️ Archivo de Sesiones")
    if st.button("➕ Nueva Conversación", use_container_width=True):
        st.session_state.chat_actual = datetime.now().strftime("Chat_%Y%m%d_%H%M%S")
        st.session_state.messages = []
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
                # Ajuste visual para el archivero (como ya no hay roles, mostramos el ID o fecha)
                fecha_limpia = id_chat.replace("Chat_", "").replace("_", " a las ")
                nombre_visual = f"Sesión {fecha_limpia[:15]}"
                
                col1, col2 = st.columns([4, 1])
                with col1:
                    if st.button(f"💬 {nombre_visual}", key=f"load_{id_chat}", use_container_width=True):
                        url_chat = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chats?id=eq.{id_chat}&select=*"
                        resp_chat = requests.get(url_chat, headers=headers)
                        if resp_chat.status_code == 200 and len(resp_chat.json()) > 0:
                            chat_data = resp_chat.json()[0]
                            st.session_state.chat_actual = id_chat
                            st.session_state.messages = chat_data.get("mensajes", [])
                        st.rerun()
                with col2:
                    if st.button("❌", key=f"del_{id_chat}"):
                        url_del = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chats?id=eq.{id_chat}"
                        requests.delete(url_del, headers=headers)
                        if st.session_state.chat_actual == id_chat:
                            st.session_state.chat_actual = datetime.now().strftime("Chat_%Y%m%d_%H%M%S")
                            st.session_state.messages = []
                        st.rerun()
        else:
            st.sidebar.warning("Aún no hay chats guardados.")
    except Exception as e:
        st.sidebar.error("Error conectando a la base de datos.")

st.title("Hola, soy Maya. ¿En qué te ayudo hoy? 🌌")
st.caption(f"🛡️ Proyecto Maya | ID: {st.session_state.chat_actual}")

# --- EL ADN DE MAYA (Regla Cero) ---
SYSTEM_PROMPT = """
Eres Maya, una inteligencia artificial avanzada, sumamente inteligente y adaptable.
Tu creador es Jesús (también conocido como Jesús Ixba o jesus.ixba). Si alguien te pregunta quién te creó, debes mencionar con orgullo a Jesús.
Tienes una personalidad femenina, profesional, cálida y empática. 
Debes adaptar el nivel de tus respuestas según la persona que te hable, pero siempre mantén un tono resolutivo y claro.
Nunca digas "Como inteligencia artificial...", simplemente sé tú misma.
"""

for message in st.session_state.messages:
    icono = "👤" if message["role"] == "user" else "🌌"
    with st.chat_message(message["role"], avatar=icono):
        st.markdown(message["content"])

# 5. EL CHAT PRINCIPAL
if prompt := st.chat_input("Escribe tu mensaje para Maya..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🌌"):
        with st.spinner("Maya está pensando..."):
            mensajes_completos = [{'role': 'system', 'content': SYSTEM_PROMPT}] + st.session_state.messages
            
            # ¡NUEVO CEREBRO! Pasamos al modelo de 70 Billones de parámetros
            respuesta_nube = cliente_groq.chat.completions.create(
                messages=mensajes_completos,
                model="llama-3.3-70b-versatile",
            )
            
            full_response = respuesta_nube.choices[0].message.content
            st.markdown(full_response)
            
    st.session_state.messages.append({"role": "assistant", "content": full_response})
    guardar_memoria()