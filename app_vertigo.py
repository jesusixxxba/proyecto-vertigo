import streamlit as st
import requests
import re
from datetime import datetime
from openai import OpenAI
import io
import base64
from PIL import Image

# ===================== CONFIGURACIÓN =====================
st.set_page_config(
    page_title="Maya | IxInteractive Studios",
    page_icon="🌌",
    layout="centered",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #0a0e17; color: #e6edf3; }
    .main-header {
        font-size: 2.8rem;
        font-weight: 700;
        background: linear-gradient(90deg, #a5d6ff, #58a6ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.3rem;
    }
    .subtitle {
        text-align: center;
        color: #8b949e;
        font-size: 1.15rem;
        margin-bottom: 2rem;
    }
    .stChatMessage {
        border-radius: 18px;
        padding: 14px 18px;
        margin-bottom: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    }
    .stChatMessage.user { background-color: #1f2a44; border-bottom-right-radius: 4px; }
    .stChatMessage.assistant { background-color: #16213e; border-bottom-left-radius: 4px; }
</style>
""", unsafe_allow_html=True)

# ===================== LLAVES =====================
MI_LLAVE_GROQ = st.secrets["MI_LLAVE_GROQ"]
MI_LLAVE_GEMINI = st.secrets["MI_LLAVE_GEMINI"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

cliente_groq = OpenAI(api_key=MI_LLAVE_GROQ, base_url="https://api.groq.com/openai/v1")
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
    if not st.session_state.messages:
        return
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chats"
    datos = {
        "id": st.session_state.chat_actual,
        "mensajes": st.session_state.messages,
        "usuario_id": st.session_state.usuario_id
    }
    try:
        requests.post(url, headers=headers, json=datos)
    except:
        pass

# ===================== SIDEBAR =====================
with st.sidebar:
    st.image("https://via.placeholder.com/160x160/1f2a44/58a6ff?text=🌌+Maya", width=140)
    st.title("Maya AI")
    st.caption(f"Usuario: **{st.session_state.usuario_id}**")
    
    col_n, col_s = st.columns(2)
    with col_n:
        if st.button("➕ Nuevo Chat", use_container_width=True):
            guardar_memoria()          # Guarda el chat actual ANTES de crear uno nuevo
            st.session_state.chat_actual = datetime.now().strftime("Chat_%Y%m%d_%H%M%S")
            st.session_state.messages = []
            st.rerun()
    with col_s:
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            guardar_memoria()
            st.session_state.clear()
            st.rerun()
    
    st.markdown("---")
    st.subheader("📂 Chats Guardados")
    
    try:
        url_get = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chats"
        params = {"usuario_id": f"eq.{st.session_state.usuario_id}", "select": "id,mensajes"}
        res_db = requests.get(url_get, headers=headers, params=params)
        
        if res_db.status_code == 200:
            chats_viejos = res_db.json()
            chats_viejos.sort(key=lambda x: x["id"], reverse=True)
            
            for chat in chats_viejos:
                chat_id = chat["id"]
                label = chat_id.replace("Chat_", "").replace("_", " ")[:22]
                col_btn, col_del = st.columns([4, 1])
                with col_btn:
                    if st.button(f"💬 {label}", key=f"load_{chat_id}", use_container_width=True):
                        guardar_memoria()   # Guarda el actual antes de cambiar
                        st.session_state.chat_actual = chat_id
                        st.session_state.messages = chat.get("mensajes", [])
                        st.rerun()
                with col_del:
                    if st.button("🗑️", key=f"del_{chat_id}"):
                        requests.delete(url_get, headers=headers, params={"id": f"eq.{chat_id}"})
                        st.rerun()
    except:
        st.caption("No se pudieron cargar los chats.")

# ===================== CHAT PRINCIPAL =====================
st.markdown('<h1 class="main-header">Hola, soy Maya 🌌</h1>', unsafe_allow_html=True)
st.caption("¿En qué puedo ayudarte hoy?")

# Mostrar mensajes
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🌌"):
        if msg.get("content"):
            st.markdown(msg["content"])
        if msg.get("image"):
            st.image(msg["image"], width=380)

# Entrada del usuario
if prompt := st.chat_input("Escribe tu mensaje o sube una imagen...", accept_file=True, file_type=["jpg", "png", "jpeg"]):
    img_url = None
    txt_u = prompt.text if hasattr(prompt, "text") else str(prompt)

    if prompt.files:
        try:
            img = Image.open(prompt.files[0])
            buf = io.BytesIO()
            img.save(buf, format=img.format or "PNG")
            img_url = f"data:image/{(img.format or 'png').lower()};base64,{base64.b64encode(buf.getvalue()).decode()}"
        except:
            st.error("No se pudo procesar la imagen")

    st.session_state.messages.append({"role": "user", "content": txt_u, "image": img_url})
    st.rerun()

# ===================== RESPUESTA =====================
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant", avatar="🌌"):
        with st.spinner("Maya está pensando..."):
            system_prompt = """
            Eres Maya, una IA versátil, cálida, inteligente y creativa de IxInteractive Studios.
            Puedes ayudar con cualquier cosa que el usuario necesite.
            Adáptate completamente a la conversación.
            """

            hist = [{"role": "system", "content": system_prompt}]
            for m in st.session_state.messages:
                if m.get("image"):
                    content = [
                        {"type": "text", "text": m.get("content", "Analiza esta imagen")},
                        {"type": "image_url", "image_url": {"url": m["image"]}}
                    ]
                else:
                    content = m.get("content", "")
                hist.append({"role": m["role"], "content": content})

            opciones = [
                {"cliente": cliente_groq, "modelo": "llama-3.3-70b-versatile"},
                {"cliente": cliente_gemini, "modelo": "gemini-2.5-flash"},
            ]

            txt_res = None
            for op in opciones:
                try:
                    res = op["cliente"].chat.completions.create(
                        model=op["modelo"], 
                        messages=hist, 
                        temperature=0.78, 
                        max_tokens=1200
                    )
                    txt_res = res.choices[0].message.content
                    break
                except:
                    continue

            if txt_res:
                st.markdown(txt_res)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": txt_res,
                    "image": None
                })
                guardar_memoria()
                st.rerun()
            else:
                st.error("🚨 No se pudo obtener respuesta.")