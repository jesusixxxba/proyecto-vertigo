import streamlit as st
import requests
import re
from datetime import datetime
from groq import Groq
from openai import OpenAI
import io
import base64
from PIL import Image

# ===================== CONFIGURACIÓN =====================
st.set_page_config(
    page_title="Maya AI | IxInteractive",
    page_icon="🌌",
    layout="centered",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #0a0e17; color: #e6edf3; }
    .main-header { font-size: 2.8rem; font-weight: 700; background: linear-gradient(90deg, #a5d6ff, #ffffff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; margin-bottom: 0.3rem; }
    .subtitle { text-align: center; color: #8b949e; font-size: 1.15rem; margin-bottom: 2rem; }
    .stChatMessage { border-radius: 18px; padding: 14px 18px; margin-bottom: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.2); }
</style>
""", unsafe_allow_html=True)

# ===================== LLAVES =====================
MI_LLAVE_GROQ = st.secrets["MI_LLAVE_GROQ"]
MI_LLAVE_GEMINI = st.secrets["MI_LLAVE_GEMINI"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

cliente_groq = Groq(api_key=MI_LLAVE_GROQ)
cliente_gemini = OpenAI(api_key=MI_LLAVE_GEMINI, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates"
}

# ===================== SESIÓN =====================
if "usuario_id" not in st.session_state:
    st.markdown('<h1 class="main-header">IxInteractive Studios</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Acceso a Maya AI</p>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        correo = st.text_input("Ingresa tu correo electrónico", placeholder="jesus@ejemplo.com")
        if st.button("🚀 Entrar a Maya", type="primary", use_container_width=True):
            if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', correo.strip()):
                st.session_state.usuario_id = correo.strip().lower()
                st.rerun()
            else:
                st.error("Por favor ingresa un correo válido")
    st.stop()

if "chat_actual" not in st.session_state:
    st.session_state.chat_actual = datetime.now().strftime("Chat_%Y%m%d_%H%M%S")
    st.session_state.messages = []

def guardar_memoria():
    if len(st.session_state.messages) == 0:
        return
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chats"
    # IMPORTANTE: Usamos 'rol' porque así está en tu Supabase
    datos = {
        "id": st.session_state.chat_actual,
        "mensajes": st.session_state.messages,
        "rol": st.session_state.usuario_id
    }
    try: requests.post(url, headers=headers, json=datos)
    except: pass

# ===================== SIDEBAR (HISTORIAL REPARADO) =====================
with st.sidebar:
    st.image("https://img.icons8.com/fluency/160/galaxy.png", width=100)
    st.title("Maya AI")
    st.caption(f"Operador: **{st.session_state.usuario_id}**")
    
    col_n, col_s = st.columns(2)
    with col_n:
        if st.button("➕ Nuevo", use_container_width=True):
            guardar_memoria()
            st.session_state.chat_actual = datetime.now().strftime("Chat_%Y%m%d_%H%M%S")
            st.session_state.messages = []
            st.rerun()
    with col_s:
        if st.button("🚪 Salir", use_container_width=True):
            guardar_memoria()
            st.session_state.clear()
            st.rerun()
    
    st.markdown("---")
    st.subheader("📂 Chats Guardados")
    
    try:
        url_get = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chats"
        # Filtramos por la columna 'rol'
        params = {"rol": f"eq.{st.session_state.usuario_id}", "select": "id,mensajes", "order": "id.desc"}
        res_db = requests.get(url_get, headers=headers, params=params)
        
        if res_db.status_code == 200:
            chats = res_db.json()
            if not chats:
                st.caption("No hay chats guardados aún.")
            for chat in chats:
                id_c = chat["id"]
                label = id_c.replace("Chat_", "").replace("_", " ")
                col_btn, col_del = st.columns([4, 1])
                with col_btn:
                    if st.button(f"💬 {label[:12]}", key=f"L_{id_c}", use_container_width=True):
                        st.session_state.chat_actual = id_c
                        st.session_state.messages = chat.get("mensajes", [])
                        st.rerun()
                with col_del:
                    if st.button("🗑️", key=f"D_{id_c}"):
                        requests.delete(url_get, headers=headers, params={"id": f"eq.{id_c}"})
                        st.rerun()
        else:
            st.error("Error al conectar con la DB")
    except:
        st.caption("Conectando con historial...")

# ===================== CHAT PRINCIPAL =====================
st.markdown('<h1 class="main-header">Hola, soy Maya 🌌</h1>', unsafe_allow_html=True)
st.caption("¿En qué puedo ayudarte hoy?")

# Mostrar mensajes
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🌌"):
        if msg.get("content"): st.markdown(msg["content"])
        if msg.get("image"): st.image(msg["image"], width=300)

# Entrada del usuario
if prompt := st.chat_input("Escribe tu mensaje...", accept_file=True, file_type=["jpg", "png", "jpeg"]):
    img_url = None
    txt_u = prompt.text if hasattr(prompt, "text") else str(prompt)

    if prompt.files:
        try:
            img = Image.open(prompt.files[0])
            img.thumbnail((800, 800))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75)
            img_url = f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"
        except:
            st.error("Error en imagen")

    st.session_state.messages.append({"role": "user", "content": txt_u, "image": img_url})
    st.rerun()

# ===================== RESPUESTA =====================
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant", avatar="🌌"):
        with st.spinner("Analizando..."):
            system_prompt = "Eres Maya, una IA de IxInteractive Studios. Técnica y eficiente."
            hist = [{"role": "system", "content": system_prompt}]
            for m in st.session_state.messages:
                if m.get("image"):
                    content = [{"type": "text", "text": m.get("content", "Analiza esto")},
                               {"type": "image_url", "image_url": {"url": m["image"]}}]
                else:
                    content = m.get("content", "")
                hist.append({"role": m["role"], "content": content})

            txt_res = None
            try:
                res = cliente_gemini.chat.completions.create(
                    model="gemini-1.5-flash",
                    messages=hist,
                    temperature=0.7
                )
                txt_res = res.choices[0].message.content
            except:
                try:
                    res = cliente_groq.chat.completions.create(
                        messages=[h for h in hist if isinstance(h["content"], str)],
                        model="llama-3.3-70b-versatile"
                    )
                    txt_res = res.choices[0].message.content
                except Exception as e:
                    st.error(f"Error: {str(e)}")

            if txt_res:
                st.markdown(txt_res)
                st.session_state.messages.append({"role": "assistant", "content": txt_res, "image": None})
                guardar_memoria()
                st.rerun()