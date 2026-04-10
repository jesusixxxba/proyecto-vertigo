import streamlit as st
import requests
import re
from datetime import datetime
from groq import Groq
from tavily import TavilyClient

# ===================== 1. CONFIGURACIÓN =====================
MI_LLAVE_GROQ = st.secrets["MI_LLAVE_GROQ"]
TAVILY_API_KEY = st.secrets["TAVILY_API_KEY"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

cliente_groq = Groq(api_key=MI_LLAVE_GROQ)
tavily = TavilyClient(api_key=TAVILY_API_KEY)

headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}

st.set_page_config(page_title="Maya AI", page_icon="🌌", layout="centered")

# ===================== 2. ESTÉTICA PREMIUM =====================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    .stApp { background: radial-gradient(circle at top right, #1a1f2e, #0d1117); font-family: 'Inter', sans-serif; color: #c9d1d9; }
    .main-header { font-size: 3rem; font-weight: 700; background: linear-gradient(90deg, #a5d6ff, #ffffff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; margin-bottom: 20px;}
    [data-testid="stChatMessage"] { background: rgba(22, 27, 34, 0.6) !important; backdrop-filter: blur(8px); border: 1px solid rgba(48, 54, 61, 0.8); border-radius: 16px !important; margin-bottom: 10px; }
    .fuente-link { display: inline-block; background: rgba(165, 214, 255, 0.1); color: #a5d6ff; padding: 4px 10px; border-radius: 8px; font-size: 0.75rem; text-decoration: none; margin-right: 8px; border: 1px solid rgba(165, 214, 255, 0.3); }
    </style>
    """, unsafe_allow_html=True)

# ===================== 3. LÓGICA DE FILTRADO =====================

def es_charla_ligera(texto):
    # Detecta saludos, agradecimientos o confirmaciones simples
    texto = texto.lower().strip()
    # Lista de frases que NO requieren búsqueda en web
    patrones = [
        r"^(hola|hey|buenas|buenos dias|buenas tardes|buenas noches)$",
        r"^(gracias|muchas gracias|ty|thx)$",
        r"^(ok|vale|perfecto|entendido|muy bien|bien|excelente|genial)$",
        r"^(como estas|quien eres|que tal)$"
    ]
    return any(re.match(p, texto) for p in patrones) or len(texto.split()) <= 2

def investigar_web(query):
    if es_charla_ligera(query):
        return None, ""
    try:
        respuesta = tavily.search(query=query, search_depth="advanced", max_results=3)
        contexto = "\n".join([f"- {res['content']}" for res in respuesta['results']])
        links = "".join([f"<a class='fuente-link' href='{res['url']}' target='_blank'>🔗 Fuente {i+1}</a>" for i, res in enumerate(respuesta['results'])])
        return contexto, links
    except:
        return "No hay conexión a la red.", ""

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

for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="👤" if msg["role"]=="user" else "🌌"):
        st.markdown(msg["content"], unsafe_allow_html=True)

if prompt := st.chat_input("¿En qué trabajamos hoy?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🌌"):
        charla = es_charla_ligera(prompt)
        
        if charla:
            # Respuesta rápida y natural para charla ligera
            final_prompt = f"Eres Maya de IxInteractive. El usuario dice: '{prompt}'. Responde de forma muy breve, natural y amable como una asistente técnica real. No definas palabras ni traduzcas."
            links_html = ""
        else:
            # Investigación profunda para temas reales
            with st.spinner("Investigando datos de 2026..."):
                datos_web, links_html = investigar_web(prompt)
                final_prompt = f"""
                FECHA: 10 de Abril de 2026.
                CONTEXTO WEB: {datos_web}
                INSTRUCCIÓN: Responde a '{prompt}' usando el contexto. Sé técnica y directa.
                """

        try:
            res = cliente_groq.chat.completions.create(
                messages=[{"role": "user", "content": final_prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.4
            )
            txt = res.choices[0].message.content
            if links_html:
                txt += f"\n\n<div style='border-top: 1px solid #30363d; padding-top:10px;'>{links_html}</div>"
            
            st.markdown(txt, unsafe_allow_html=True)
            st.session_state.messages.append({"role": "assistant", "content": txt})
            
            # Guardar en Supabase
            requests.post(f"{SUPABASE_URL.rstrip('/')}/rest/v1/chats", headers=headers, json={
                "id": st.session_state.chat_id, "mensajes": st.session_state.messages, "rol": st.session_state.usuario_id
            })
        except Exception as e:
            st.error(f"Falla de sistema: {e}")