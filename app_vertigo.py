import streamlit as st
import requests
import re
from datetime import datetime
from groq import Groq
from openai import OpenAI   # ← Para usar Gemini
import io
import base64
from PIL import Image

# ===================== 1. CONFIGURACIÓN Y LLAVES =====================
MI_LLAVE_GROQ = st.secrets["MI_LLAVE_GROQ"]
MI_LLAVE_GEMINI = st.secrets["MI_LLAVE_GEMINI"]   # ← Asegúrate de tener esta llave
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

cliente_groq = Groq(api_key=MI_LLAVE_GROQ)
cliente_gemini = OpenAI(
    api_key=MI_LLAVE_GEMINI, 
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates"
}

st.set_page_config(page_title="Maya AI | IxInteractive", page_icon="🌌", layout="centered")

# ===================== 2. ESTÉTICA PREMIUM =====================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    
    .stApp {
        background: radial-gradient(circle at top right, #1a1f2e, #0d1117);
        font-family: 'Inter', sans-serif;
        color: #c9d1d9;
    }

    .main-header {
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(90deg, #a5d6ff, #ffffff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 10px;
        filter: drop-shadow(0px 4px 10px rgba(165, 214, 255, 0.3));
    }

    [data-testid="stChatMessage"] {
        background: rgba(22, 27, 34, 0.6) !important;
        backdrop-filter: blur(8px);
        border: 1px solid rgba(48, 54, 61, 0.8);
        border-radius: 16px !important;
        padding: 20px !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        margin-bottom: 15px;
    }

    [data-testid="stSidebar"] {
        background-color: #010409 !important;
        border-right: 1px solid #30363d;
    }

    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

def es_correo_valido(correo):
    patron = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(patron, correo) is not None

# ===================== 3. SISTEMA DE ACCESO =====================
if "usuario_id" not in st.session_state:
    st.markdown('<h1 class="main-header">IxInteractive</h1>', unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #8b949e;'>Diseñado para precisión quirúrgica</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            correo_input = st.text_input("✉️ Credencial de acceso:", placeholder="usuario@ixinteractive.com")
            if st.form_submit_button("Sincronizar Sistema", use_container_width=True):
                correo_limpio = correo_input.strip().lower()
                if es_correo_valido(correo_limpio):
                    st.session_state.usuario_id = correo_limpio
                    st.rerun()
                else:
                    st.error("🚨 Acceso denegado: Credencial inválida.")
    st.stop()

if "chat_actual" not in st.session_state:
    st.session_state.chat_actual = datetime.now().strftime("Chat_%Y%m%d_%H%M%S")
    st.session_state.messages = []

def guardar_memoria():
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chats"
    datos = {
        "id": st.session_state.chat_actual, 
        "mensajes": st.session_state.messages, 
        "rol": st.session_state.usuario_id 
    }
    try: 
        requests.post(url, headers=headers, json=datos)
    except: 
        pass

# ===================== 4. SIDEBAR =====================
with st.sidebar:
    st.title("Panel de Control")
    st.caption(f"Operador: **{st.session_state.usuario_id}**")
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("➕ Nuevo", use_container_width=True):
            st.session_state.chat_actual = datetime.now().strftime("Chat_%Y%m%d_%H%M%S")
            st.session_state.messages = []
            st.rerun()
    with c2:
        if st.button("🚪 Salir", use_container_width=True):
            st.session_state.clear()
            st.rerun()
            
    st.markdown("---")
    st.subheader("📂 Historial de Chats")
    
    try:
        url_get = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chats"
        params = {"rol": f"eq.{st.session_state.usuario_id}", "select": "id,mensajes", "order": "id.desc"}
        res_db = requests.get(url_get, headers=headers, params=params)
        
        if res_db.status_code == 200:
            for chat in res_db.json():
                id_c = chat["id"]
                label = id_c.replace("Chat_", "").replace("_", " ")
                col_b, col_d = st.columns([4, 1])
                with col_b:
                    if st.button(f"💬 {label[:12]}", key=f"L_{id_c}", use_container_width=True):
                        st.session_state.chat_actual = id_c
                        st.session_state.messages = chat.get("mensajes", [])
                        st.rerun()
                with col_d:
                    if st.button("❌", key=f"D_{id_c}"):
                        requests.delete(url_get, headers=headers, params={"id": f"eq.{id_c}"})
                        if st.session_state.chat_actual == id_c:
                            st.session_state.chat_actual = datetime.now().strftime("Chat_%Y%m%d_%H%M%S")
                            st.session_state.messages = []
                        st.rerun()
        else:
            st.sidebar.warning("Aún no tienes chats guardados.")
    except:
        st.sidebar.error("Error conectando a la base de datos.")

# ===================== 5. INTERFAZ DE CHAT =====================
st.markdown(f'<h1 class="main-header">Maya AI</h1>', unsafe_allow_html=True)

SYSTEM_PROMPT = """
Eres Maya, una inteligencia artificial técnica y avanzada de IxInteractive Studios.
REGLA CRÍTICA: Actualmente te encuentras en FASE BETA. 
No tienes acceso a internet en tiempo real, navegación web, resultados deportivos en vivo o enlaces externos actualizados. 
Si el usuario solicita enlaces, noticias de hoy o datos en tiempo real, informa amablemente que Maya está en fase Beta y que el módulo de navegación está en mantenimiento o desarrollo. 
Tu especialidad es la asistencia técnica, lógica y programación con tu base de conocimientos actual.
"""

if not st.session_state.messages:
    with st.chat_message("assistant", avatar="🌌"):
        st.markdown("👋 **Sistemas listos.** Soy Maya. ¿En qué puedo ayudarte hoy?")

for msg in st.session_state.messages:
    avatar = "👤" if msg["role"] == "user" else "🌌"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

if prompt := st.chat_input("Escribe una instrucción..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🌌"):
        with st.spinner("Procesando..."):
            hist = [{'role': 'system', 'content': SYSTEM_PROMPT}] + st.session_state.messages
            
            txt = None
            
            # === 1. Primero intentamos con Groq (rápido y barato) ===
            try:
                res = cliente_groq.chat.completions.create(
                    messages=hist,
                    model="llama-3.3-70b-versatile",
                    temperature=0.7
                )
                txt = res.choices[0].message.content
            except:
                pass

            # === 2. Si Groq falla, usamos Gemini Flash como respaldo ===
            if not txt:
                try:
                    res = cliente_gemini.chat.completions.create(
                        model="gemini-2.5-flash",      # O prueba "gemini-1.5-flash" si no funciona
                        messages=hist,
                        temperature=0.7
                    )
                    txt = res.choices[0].message.content
                except Exception as e:
                    st.error(f"Error en ambos modelos: {str(e)}")

            if txt:
                st.markdown(txt)
                st.session_state.messages.append({"role": "assistant", "content": txt})
                guardar_memoria()
                st.rerun()
            else:
                st.error("🚨 No se pudo obtener respuesta de ningún modelo.")