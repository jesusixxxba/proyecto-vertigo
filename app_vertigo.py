import streamlit as st
import json
import requests
import re
from datetime import datetime
from openai import OpenAI # <--- Cambiamos Groq por OpenAI (es compatible)

# ===================== 1. CONFIGURACIÓN Y LLAVES =====================
# Usamos la nueva llave de SambaNova
MI_LLAVE_SAMBANOVA = st.secrets["MI_LLAVE_SAMBANOVA"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

# Configuramos el cliente para SambaNova
cliente_ia = OpenAI(
    api_key=MI_LLAVE_SAMBANOVA,
    base_url="https://api.sambanova.ai/v1"
)

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates"
}

st.set_page_config(page_title="Maya | IxInteractive", page_icon="🌌", layout="centered")

# Estética IxInteractive
st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    .stChatMessage { background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin-bottom: 10px; }
    .main-header { font-size: 2.5rem; font-weight: 700; color: #a5d6ff; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

def es_correo_valido(correo):
    patron = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(patron, correo) is not None

# ===================== 2. ACCESO =====================
if "usuario_id" not in st.session_state:
    st.markdown('<h1 class="main-header">IxInteractive Studios</h1>', unsafe_allow_html=True)
    with st.form("login_form"):
        correo_input = st.text_input("✉️ Correo:", placeholder="tu@correo.com")
        if st.form_submit_button("Entrar"):
            if es_correo_valido(correo_input.strip()):
                st.session_state.usuario_id = correo_input.strip().lower()
                st.rerun()
    st.stop()

if "chat_actual" not in st.session_state:
    st.session_state.chat_actual = datetime.now().strftime("Chat_%Y%m%d_%H%M%S")
    st.session_state.messages = []

def guardar_memoria():
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chats"
    datos = {"id": st.session_state.chat_actual, "rol": st.session_state.usuario_id, "mensajes": st.session_state.messages}
    try: requests.post(url, headers=headers, json=datos)
    except: pass

# ===================== 3. SIDEBAR =====================
with st.sidebar:
    st.title("👤 Perfil")
    st.caption(f"Usuario: {st.session_state.usuario_id}")
    if st.button("➕ Nuevo Chat", use_container_width=True):
        st.session_state.chat_actual = datetime.now().strftime("Chat_%Y%m%d_%H%M%S")
        st.session_state.messages = []
        st.rerun()
    
    st.markdown("---")
    st.subheader("📂 Historial")
    try:
        url_get = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chats"
        params = {"rol": f"eq.{st.session_state.usuario_id}", "select": "id,mensajes", "order": "id.desc"}
        res_db = requests.get(url_get, headers=headers, params=params)
        if res_db.status_code == 200:
            for chat in res_db.json():
                if st.button(f"💬 {chat['id'][5:19]}", key=chat['id'], use_container_width=True):
                    st.session_state.chat_actual = chat['id']
                    st.session_state.messages = chat['mensajes']
                    st.rerun()
    except: pass

# ===================== 4. CHAT =====================
st.title("Hola, soy Maya 🌌")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="👤" if msg["role"]=="user" else "🌌"):
        st.markdown(msg["content"])

if prompt := st.chat_input("Escribe a Maya..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🌌"):
        with st.spinner("Maya pensando (SambaNova 405B)..."):
            hist = [{"role": "system", "content": "Eres Maya, la IA más potente de IxInteractive Studios."}] + st.session_state.messages
            try:
                # LLAMADA AL MODELO MÁS POTENTE DEL MUNDO (405B)
                res = cliente_ia.chat.completions.create(
                    model="Meta-Llama-3.3-70B-Instruct",
                    messages=hist,
                    temperature=0.7
                )
                txt = res.choices[0].message.content
                st.markdown(txt)
                st.session_state.messages.append({"role": "assistant", "content": txt})
                guardar_memoria()
            except Exception as e:
                st.error(f"🚨 Fallo en motor SambaNova: {e}")