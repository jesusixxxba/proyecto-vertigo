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

st.set_page_config(page_title="Maya AI | IxInteractive", page_icon="🌌", layout="centered")

# ===================== 2. ESTÉTICA DE ELITE (CSS) =====================
st.markdown("""
    <style>
    /* Fondo General y Tipografía */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    
    .stApp {
        background: radial-gradient(circle at top right, #1a1f2e, #0d1117);
        font-family: 'Inter', sans-serif;
        color: #c9d1d9;
    }

    /* Títulos con Brillo */
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

    /* Burbujas de Chat (Glassmorphism) */
    [data-testid="stChatMessage"] {
        background: rgba(22, 27, 34, 0.6) !important;
        backdrop-filter: blur(8px);
        border: 1px solid rgba(48, 54, 61, 0.8);
        border-radius: 16px !important;
        padding: 20px !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        margin-bottom: 15px;
    }

    /* Sidebar Refinado */
    [data-testid="stSidebar"] {
        background-color: #010409 !important;
        border-right: 1px solid #30363d;
    }

    /* Botón Flotante de Scroll (Elegante) */
    #ir-abajo {
        position: fixed;
        bottom: 90px;
        right: 40px;
        z-index: 1000;
        background: rgba(31, 41, 55, 0.8);
        backdrop-filter: blur(4px);
        color: #a5d6ff;
        width: 45px;
        height: 45px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        text-decoration: none;
        border: 1px solid rgba(165, 214, 255, 0.4);
        transition: all 0.3s ease;
    }
    #ir-abajo:hover {
        transform: translateY(-5px);
        background: #a5d6ff;
        color: #0d1117;
        box-shadow: 0 0 20px rgba(165, 214, 255, 0.5);
    }

    /* Ocultar barra de Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- Validación de Correo ---
def es_correo_valido(correo):
    patron = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(patron, correo) is not None

# ===================== 3. SISTEMA DE ACCESO =====================
if "usuario_id" not in st.session_state:
    st.markdown('<h1 class="main-header">IxInteractive</h1>', unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #8b949e;'>Engineered for surgical precision</p>", unsafe_allow_html=True)
    
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("login_form"):
                correo_input = st.text_input("✉️ Credencial de acceso:", placeholder="usuario@ixinteractive.com")
                if st.form_submit_button("Sincronizar", use_container_width=True):
                    correo_limpio = correo_input.strip().lower()
                    if es_correo_valido(correo_limpio):
                        st.session_state.usuario_id = correo_limpio
                        st.rerun()
                    else:
                        st.error("🚨 Acceso denegado: Correo inválido.")
    st.stop()

# Mostrar botón de bajada solo si está logueado
st.markdown('<a id="ir-abajo" href="#ultimo-mensaje">▼</a>', unsafe_allow_html=True)

# Inicialización de sesión
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

# ===================== 4. SIDEBAR (DASHBOARD) =====================
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/galaxy.png", width=60)
    st.title("Control Panel")
    st.caption(f"Operator: **{st.session_state.usuario_id}**")
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("➕ New", use_container_width=True):
            st.session_state.chat_actual = datetime.now().strftime("Chat_%Y%m%d_%H%M%S")
            st.session_state.messages = []
            st.rerun()
    with c2:
        if st.button("🚪 Exit", use_container_width=True):
            st.session_state.clear()
            st.rerun()
            
    st.markdown("<br><p style='font-size: 0.8rem; color: #8b949e;'>SYSTEM LOGS</p>", unsafe_allow_html=True)
    
    try:
        url_get = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chats"
        params = {"rol": f"eq.{st.session_state.usuario_id}", "select": "id,mensajes", "order": "id.desc"}
        res_db = requests.get(url_get, headers=headers, params=params)
        
        if res_db.status_code == 200:
            for chat in res_db.json():
                id_c = chat["id"]
                label = id_c.replace("Chat_", "").replace("_", " ")
                col_btn, col_del = st.columns([5, 1])
                with col_btn:
                    if st.button(f"● {label[:10]}", key=f"L_{id_c}", use_container_width=True):
                        st.session_state.chat_actual = id_c
                        st.session_state.messages = chat.get("mensajes", [])
                        st.rerun()
                with col_del:
                    if st.button("×", key=f"D_{id_c}"):
                        requests.delete(url_get, headers=headers, params={"id": f"eq.{id_c}"})
                        st.rerun()
    except:
        st.caption("Link offline...")

# ===================== 5. INTERFAZ DE CHAT =====================
st.markdown(f'<h1 class="main-header">Maya AI</h1>', unsafe_allow_html=True)

SYSTEM_PROMPT = "Eres Maya, una IA de IxInteractive Studios. Responde con precisión técnica y brevedad profesional."

# Saludo inicial refinado
if not st.session_state.messages:
    with st.chat_message("assistant", avatar="🌌"):
        st.markdown("👋 **Sistemas listos.** Soy Maya. ¿Cuál es el objetivo de hoy?")

# Mensajes
for msg in st.session_state.messages:
    avatar = "👤" if msg["role"] == "user" else "🌌"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# Input con estilo
if prompt := st.chat_input("Escribe una instrucción..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🌌"):
        with st.spinner("Procesando..."):
            hist = [{'role': 'system', 'content': SYSTEM_PROMPT}] + st.session_state.messages
            try:
                res = cliente_groq.chat.completions.create(
                    messages=hist,
                    model="llama-3.3-70b-versatile",
                    temperature=0.7
                )
                full_response = res.choices[0].message.content
                st.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                guardar_memoria()
                st.rerun()
            except Exception as e:
                st.error(f"Hardware Error: {e}")

st.markdown('<div id="ultimo-mensaje"></div>', unsafe_allow_html=True)