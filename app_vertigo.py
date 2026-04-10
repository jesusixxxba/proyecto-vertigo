import streamlit as st
import json
import requests
import re
from datetime import datetime
from groq import Groq
from duckduckgo_search import DDGS

# ===================== 1. CONFIGURACIÓN =====================
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

# ===================== 2. ESTÉTICA PREMIUM =====================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    .stApp { background: radial-gradient(circle at top right, #1a1f2e, #0d1117); font-family: 'Inter', sans-serif; color: #c9d1d9; }
    .main-header { font-size: 3rem; font-weight: 700; background: linear-gradient(90deg, #a5d6ff, #ffffff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; filter: drop-shadow(0px 4px 10px rgba(165,214,255,0.3)); }
    [data-testid="stChatMessage"] { background: rgba(22, 27, 34, 0.6) !important; backdrop-filter: blur(8px); border: 1px solid rgba(48, 54, 61, 0.8); border-radius: 16px !important; padding: 20px !important; }
    .fuente-link { display: inline-block; background: rgba(165, 214, 255, 0.1); color: #a5d6ff; padding: 4px 10px; border-radius: 8px; font-size: 0.75rem; text-decoration: none; margin-right: 8px; border: 1px solid rgba(165, 214, 255, 0.3); }
    #ir-abajo { position: fixed; bottom: 90px; right: 40px; z-index: 1000; background: rgba(31, 41, 55, 0.8); color: #a5d6ff; width: 45px; height: 45px; display: flex; align-items: center; justify-content: center; border-radius: 50%; border: 1px solid rgba(165,214,255,0.4); text-decoration: none; }
    </style>
    """, unsafe_allow_html=True)

# ===================== 3. MOTOR DE BÚSQUEDA 2026 =====================

def buscar_en_web(query):
    # Forzamos la búsqueda al año actual
    query_modificada = f"{query} lanzamientos y precios abril 2026"
    contexto = ""
    links = []
    try:
        with DDGS() as ddgs:
            # Buscamos resultados frescos
            busqueda = ddgs.text(query_modificada, max_results=5)
            for i, r in enumerate(busqueda):
                contexto += f"\nNOTICIA {i+1}: {r['body']}\n"
                links.append(f"<a class='fuente-link' href='{r['href']}' target='_blank'>🔗 Fuente {i+1}</a>")
    except Exception as e:
        contexto = f"Error en búsqueda: {str(e)}"
    return contexto, "".join(links)

# ===================== 4. ACCESO =====================
if "usuario_id" not in st.session_state:
    st.markdown('<h1 class="main-header">IxInteractive</h1>', unsafe_allow_html=True)
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("login"):
                correo = st.text_input("✉️ Credencial:", placeholder="usuario@ixinteractive.com")
                if st.form_submit_button("Sincronizar", use_container_width=True):
                    if correo:
                        st.session_state.usuario_id = correo.strip().lower()
                        st.rerun()
    st.stop()

if "chat_actual" not in st.session_state:
    st.session_state.chat_actual = datetime.now().strftime("Chat_%Y%m%d_%H%M%S")
    st.session_state.messages = []

def guardar_memoria():
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chats"
    datos = {"id": st.session_state.chat_actual, "mensajes": st.session_state.messages, "rol": st.session_state.usuario_id}
    try: requests.post(url, headers=headers, json=datos)
    except: pass

# ===================== 5. SIDEBAR =====================
with st.sidebar:
    st.title("Panel de Control")
    if st.button("➕ Nuevo Chat", use_container_width=True):
        st.session_state.chat_actual = datetime.now().strftime("Chat_%Y%m%d_%H%M%S")
        st.session_state.messages = []
        st.rerun()
    st.markdown("---")
    try:
        url_get = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chats"
        params = {"rol": f"eq.{st.session_state.usuario_id}", "select": "id,mensajes", "order": "id.desc"}
        res_db = requests.get(url_get, headers=headers, params=params)
        for chat in res_db.json():
            label = chat['id'].replace("Chat_", "").replace("_", " ")
            if st.button(f"💬 {label[:12]}", key=chat['id'], use_container_width=True):
                st.session_state.chat_actual = chat['id']
                st.session_state.messages = chat['mensajes']
                st.rerun()
    except: pass

# ===================== 6. INTERFAZ DE CHAT =====================
st.markdown('<h1 class="main-header">Maya AI</h1>', unsafe_allow_html=True)
st.markdown('<a id="ir-abajo" href="#ultimo-mensaje">▼</a>', unsafe_allow_html=True)

# Saludo inicial si no hay mensajes
if not st.session_state.messages:
    with st.chat_message("assistant", avatar="🌌"):
        st.markdown("👋 **Sistemas listos.** Soy Maya. ¿Cuál es el objetivo de hoy?")

# Dibujar historial
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="👤" if msg["role"]=="user" else "🌌"):
        st.markdown(msg["content"], unsafe_allow_html=True)

# Procesar entrada
if prompt := st.chat_input("Escribe una instrucción..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🌌"):
        with st.spinner("Investigando lanzamientos 2026..."):
            contexto_web, links_html = buscar_en_web(prompt)
            
            # PROMPT ULTRA-AGRESIVO PARA EVITAR DESACTUALIZACIÓN
            SYSTEM_PROMPT = f"""
            Eres Maya de IxInteractive Studios. FECHA ACTUAL: 9 de Abril de 2026.
            REGLA DE ORO: Ignora tus datos de entrenamiento si contradicen la realidad de 2026. 
            No recomiendes hardware de años anteriores (S23, iPhone 14, etc.) a menos que el usuario lo pida.
            DATOS REALES DE LA WEB (2026): {contexto_web}
            Usa el contexto web para dar una respuesta moderna y precisa.
            """
            
            hist = [{'role': 'system', 'content': SYSTEM_PROMPT}] + st.session_state.messages
            
            try:
                res = cliente_groq.chat.completions.create(
                    messages=hist,
                    model="llama-3.3-70b-versatile",
                    temperature=0.2 # Mínima creatividad, máxima precisión de datos
                )
                respuesta_final = res.choices[0].message.content
                
                if links_html:
                    respuesta_final += f"\n\n<div style='border-top: 1px solid #30363d; padding-top:10px;'>{links_html}</div>"
                
                st.markdown(respuesta_final, unsafe_allow_html=True)
                st.session_state.messages.append({"role": "assistant", "content": respuesta_final})
                guardar_memoria()
                st.rerun()
            except Exception as e:
                st.error(f"Error de motor: {e}")

st.markdown('<div id="ultimo-mensaje"></div>', unsafe_allow_html=True)