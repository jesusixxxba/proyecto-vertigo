import streamlit as st
import requests
import re
from datetime import datetime
from groq import Groq
from tavily import TavilyClient # <--- El nuevo estándar

# ===================== 1. CONFIGURACIÓN =====================
MI_LLAVE_GROQ = st.secrets["MI_LLAVE_GROQ"]
TAVILY_API_KEY = st.secrets["TAVILY_API_KEY"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

cliente_groq = Groq(api_key=MI_LLAVE_GROQ)
tavily = TavilyClient(api_key=TAVILY_API_KEY)

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

st.set_page_config(page_title="Maya AI", page_icon="🌌", layout="centered")

# ===================== 2. ESTÉTICA PREMIUM =====================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    .stApp { background: radial-gradient(circle at top right, #1a1f2e, #0d1117); font-family: 'Inter', sans-serif; color: #c9d1d9; }
    .main-header { font-size: 3rem; font-weight: 700; background: linear-gradient(90deg, #a5d6ff, #ffffff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; }
    [data-testid="stChatMessage"] { background: rgba(22, 27, 34, 0.6) !important; backdrop-filter: blur(8px); border: 1px solid rgba(48, 54, 61, 0.8); border-radius: 16px !important; }
    .fuente-link { display: inline-block; background: rgba(165, 214, 255, 0.1); color: #a5d6ff; padding: 4px 10px; border-radius: 8px; font-size: 0.75rem; text-decoration: none; margin-right: 8px; border: 1px solid rgba(165, 214, 255, 0.3); }
    </style>
    """, unsafe_allow_html=True)

# ===================== 3. MOTOR DE BÚSQUEDA TAVILY =====================

def investigar_web(query):
    try:
        # Tavily busca, resume y extrae links automáticamente
        respuesta = tavily.search(query=query, search_depth="advanced", max_results=3)
        contexto = ""
        links = []
        for i, res in enumerate(respuesta['results']):
            contexto += f"\n- {res['content']}\n"
            links.append(f"<a class='fuente-link' href='{res['url']}' target='_blank'>🔗 Fuente {i+1}</a>")
        return contexto, "".join(links)
    except:
        return "No se encontraron datos actualizados.", ""

# ===================== 4. ACCESO =====================
if "usuario_id" not in st.session_state:
    st.markdown('<h1 class="main-header">IxInteractive</h1>', unsafe_allow_html=True)
    with st.form("login"):
        correo = st.text_input("✉️ Credencial:", placeholder="usuario@ixinteractive.com")
        if st.form_submit_button("Sincronizar"):
            if correo:
                st.session_state.usuario_id = correo.strip().lower()
                st.rerun()
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_id" not in st.session_state:
    st.session_state.chat_id = datetime.now().strftime("Chat_%Y%m%d_%H%M%S")

# ===================== 5. INTERFAZ =====================
st.markdown('<h1 class="main-header">Maya AI</h1>', unsafe_allow_html=True)

# Dibujar historial
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="👤" if msg["role"]=="user" else "🌌"):
        st.markdown(msg["content"], unsafe_allow_html=True)

if prompt := st.chat_input("¿Qué investigamos hoy?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🌌"):
        with st.spinner("Consultando bases de datos en tiempo real..."):
            # 1. Investigar
            datos_web, links_html = investigar_web(prompt)
            
            # 2. Inyectar Contexto (Aquí está el truco: se lo damos como "Hechos")
            PROMPT_FINAL = f"""
            FECHA ACTUAL: 9 de Abril de 2026.
            INFORMACIÓN RECUPERADA DE LA WEB:
            {datos_web}

            INSTRUCCIÓN: Basándote ÚNICAMENTE en la información de arriba, responde a la duda: "{prompt}". 
            Si la información contiene resultados deportivos o noticias de 2026, dálos con absoluta seguridad.
            """
            
            try:
                res = cliente_groq.chat.completions.create(
                    messages=[{"role": "user", "content": PROMPT_FINAL}],
                    model="llama-3.3-70b-versatile",
                    temperature=0.1
                )
                txt = res.choices[0].message.content
                if links_html:
                    txt += f"\n\n<div style='border-top: 1px solid #30363d; padding-top:10px;'>{links_html}</div>"
                
                st.markdown(txt, unsafe_allow_html=True)
                st.session_state.messages.append({"role": "assistant", "content": txt})
                
                # Guardar en Supabase
                url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chats"
                requests.post(url, headers=headers, json={
                    "id": st.session_state.chat_id, 
                    "mensajes": st.session_state.messages, 
                    "rol": st.session_state.usuario_id
                })
            except Exception as e:
                st.error(f"Falla de motor: {e}")