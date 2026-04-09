import streamlit as st
import requests
import re
from datetime import datetime
from openai import OpenAI
import io
import base64
from PIL import Image
import streamlit.components.v1 as components

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
MI_LLAVE_ELEVENLABS = st.secrets["MI_LLAVE_ELEVENLABS"]
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

# ===================== SIDEBAR (HISTORIAL REPARADO) =====================
with st.sidebar:
    st.title("Maya AI")
    st.caption(f"Usuario: **{st.session_state.usuario_id}**")
    
    col_n, col_s = st.columns(2)
    with col_n:
        if st.button("➕ Nuevo", use_container_width=True):
            st.session_state.chat_actual = datetime.now().strftime("Chat_%Y%m%d_%H%M%S")
            st.session_state.messages = []
            st.rerun()
    with col_s:
        if st.button("🚪 Salir", use_container_width=True):
            st.session_state.clear()
            st.rerun()
            
    st.markdown("---")
    st.subheader("📂 Chats Guardados")
    
    # AQUÍ ESTÁ LA MAGIA: Recuperar chats de Supabase
    try:
        url_get = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chats"
        params = {"usuario_id": f"eq.{st.session_state.usuario_id}", "select": "id,mensajes"}
        res_db = requests.get(url_get, headers=headers, params=params)
        
        if res_db.status_code == 200:
            chats_viejos = res_db.json()
            # Ordenar por el más reciente
            chats_viejos.sort(key=lambda x: x["id"], reverse=True)
            
            for chat in chats_viejos:
                id_c = chat["id"]
                label = id_c.replace("Chat_", "").replace("_", " ")
                
                col_btn, col_del = st.columns([4, 1])
                with col_btn:
                    if st.button(f"💬 {label[:14]}", key=f"load_{id_c}", use_container_width=True):
                        st.session_state.chat_actual = id_c
                        st.session_state.messages = chat.get("mensajes", [])
                        st.rerun()
                with col_del:
                    if st.button("🗑️", key=f"del_{id_c}"):
                        requests.delete(url_get, headers=headers, params={"id": f"eq.{id_c}"})
                        st.rerun()
    except:
        st.caption("No se pudieron cargar los chats.")

# ===================== CHAT PRINCIPAL =====================
st.markdown('<h1 class="main-header">Hola, soy Maya 🌌</h1>', unsafe_allow_html=True)
st.caption(f"🛡️ Sesión activa: {st.session_state.chat_actual}")

# Mostrar mensajes e imágenes
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🌌"):
        if msg.get("content"):
            st.markdown(msg["content"])
        if msg.get("image"):
            st.image(msg["image"], width=380)
        
        # EL BOTÓN DE AUDIO (Restaurado)
        if msg.get("audio"):
            aud_id = f"aud_{i}"
            audio_html = f"""
            <div style="margin-top: 10px;">
                <audio id="{aud_id}" src="data:audio/mp3;base64,{msg['audio']}"></audio>
                <button onclick="var a = document.getElementById('{aud_id}'); if(a.paused){{a.play(); this.textContent='⏸️';}} else {{a.pause(); this.textContent='▶️';}}" 
                style="background:#1f2a44; color:white; border:1px solid #58a6ff; padding:5px 15px; border-radius:15px; cursor:pointer;">
                ▶️ Escuchar
                </button>
            </div>
            """
            components.html(audio_html, height=45)

# Entrada
if prompt := st.chat_input("Escribe tu mensaje...", accept_file=True, file_type=["jpg", "png", "jpeg"]):
    img_url = None
    txt_u = prompt.text if hasattr(prompt, "text") else str(prompt)

    if prompt.files:
        img = Image.open(prompt.files[0])
        buf = io.BytesIO()
        img.save(buf, format=img.format or "PNG")
        img_url = f"data:image/{(img.format or 'png').lower()};base64,{base64.b64encode(buf.getvalue()).decode()}"

    st.session_state.messages.append({"role": "user", "content": txt_u, "image": img_url})
    st.rerun()

# Respuesta
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant", avatar="🌌"):
        with st.spinner("Maya pensando..."):
            hist = [{"role": "system", "content": "Eres Maya, IA de IxInteractive Studios."}]
            for m in st.session_state.messages:
                if m.get("image"):
                    content = [{"type": "text", "text": m.get("content", "Analiza esto")}, {"type": "image_url", "image_url": {"url": m["image"]}}]
                else: content = m.get("content", "")
                hist.append({"role": m["role"], "content": content})

            opciones = [
                {"cliente": cliente_groq, "modelo": "llama-3.3-70b-versatile"},
                {"cliente": cliente_gemini, "modelo": "gemini-2.5-flash"},
            ]

            txt_res = None
            for op in opciones:
                try:
                    res = op["cliente"].chat.completions.create(model=op["modelo"], messages=hist)
                    txt_res = res.choices[0].message.content
                    break
                except: continue

            if txt_res:
                st.markdown(txt_res)
                
                # VOZ ELEVENLABS
                aud_b64 = None
                try:
                    v_res = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/EXAVITQu4vr4xnSDxMaL", 
                        json={"text": txt_res.replace("*",""), "model_id": "eleven_multilingual_v2"}, 
                        headers={"xi-api-key": MI_LLAVE_ELEVENLABS, "Content-Type": "application/json"})
                    if v_res.status_code == 200: aud_b64 = base64.b64encode(v_res.content).decode()
                except: pass

                st.session_state.messages.append({"role": "assistant", "content": txt_res, "audio": aud_b64})
                guardar_memoria()
                st.rerun()