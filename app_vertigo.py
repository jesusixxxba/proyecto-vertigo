import streamlit as st
import json
import requests
import re
from datetime import datetime
from openai import OpenAI
import io
import base64
import streamlit.components.v1 as components

# --- LAS LLAVES DE LA NUBE (Asegúrate de tenerlas en Secrets) ---
MI_LLAVE_GROQ = st.secrets["MI_LLAVE_GROQ"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
MI_LLAVE_ELEVENLABS = st.secrets["MI_LLAVE_ELEVENLABS"]

# Conectamos a Groq (Motor de alta velocidad)
cliente_ia = OpenAI(
    api_key=MI_LLAVE_GROQ, 
    base_url="https://api.groq.com/openai/v1"
)

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates"
}

st.set_page_config(page_title="Maya | IxInteractive", page_icon="🌌")
st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    .stChatMessage { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 15px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

def es_correo_valido(correo):
    patron = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(patron, correo) is not None

# ==========================================
# 1. SISTEMA DE ACCESO
# ==========================================
if "usuario_id" not in st.session_state:
    st.title("🏢 IxInteractive Studios")
    st.subheader("Acceso a Maya AI")
    st.markdown("Ingresa tu correo para acceder a tu entorno privado.")
    
    with st.form("login_form"):
        correo_input = st.text_input("✉️ Correo electrónico:", placeholder="tu@correo.com")
        submit_button = st.form_submit_button("Iniciar Sesión", use_container_width=True)
        
        if submit_button:
            correo_limpio = correo_input.strip().lower()
            if es_correo_valido(correo_limpio):
                st.session_state.usuario_id = correo_limpio
                st.rerun()
            else:
                st.error("🚨 Por favor, ingresa un correo válido.")
    st.stop()

# ==========================================
# 2. SISTEMA DE MEMORIA (SUPABASE)
# ==========================================
if "chat_actual" not in st.session_state:
    st.session_state.chat_actual = datetime.now().strftime("Chat_%Y%m%d_%H%M%S")
    st.session_state.messages = []

def guardar_memoria():
    datos = {
        "id": st.session_state.chat_actual,
        "mensajes": st.session_state.messages,
        "usuario_id": st.session_state.usuario_id 
    }
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chats"
    try:
        requests.post(url, headers=headers, json=datos)
    except:
        pass

# ==========================================
# 3. EL ARCHIVERO (SIDEBAR)
# ==========================================
with st.sidebar:
    st.title("👤 Mi Perfil")
    st.caption(f"Conectado: **{st.session_state.usuario_id}**")
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.clear()
        st.rerun()
    st.markdown("---")
    if st.button("➕ Nueva Conversación", use_container_width=True):
        st.session_state.chat_actual = datetime.now().strftime("Chat_%Y%m%d_%H%M%S")
        st.session_state.messages = []
        st.rerun()
    st.markdown("---")
    st.subheader("Chats Privados")
    try:
        url_get = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chats"
        params = {"usuario_id": f"eq.{st.session_state.usuario_id}", "select": "id"}
        resp = requests.get(url_get, headers=headers, params=params)
        if resp.status_code == 200:
            for archivo in sorted(resp.json(), key=lambda x: x["id"], reverse=True):
                id_chat = archivo["id"]
                col1, col2 = st.columns([4, 1])
                with col1:
                    if st.button(f"💬 {id_chat[:15]}...", key=f"L_{id_chat}", use_container_width=True):
                        p = {"id": f"eq.{id_chat}", "select": "*"}
                        r = requests.get(url_get, headers=headers, params=p)
                        if r.status_code == 200 and r.json():
                            st.session_state.chat_actual = id_chat
                            st.session_state.messages = r.json()[0].get("mensajes", [])
                            st.rerun()
                with col2:
                    if st.button("❌", key=f"D_{id_chat}"):
                        requests.delete(url_get, headers=headers, params={"id": f"eq.{id_chat}"})
                        st.rerun()
    except:
        pass

# ==========================================
# 4. INTERFAZ Y LÓGICA DE MAYA
# ==========================================
st.title("Hola, soy Maya. ¿En qué te ayudo? 🌌")
st.caption(f"🛡️ IxInteractive Studios | ID: {st.session_state.chat_actual}")

SYSTEM_PROMPT = """
Eres Maya, una IA de IxInteractive Studios. Eres femenina, profesional y cálida.
REGLA DE ORO: Solo menciona a IxInteractive Studios si te preguntan quién te creó.
No menciones nombres personales (Jesús/Ixba). Sé resolutiva.
"""

# Mostrar historial
for i, msg in enumerate(st.session_state.messages):
    avatar = "👤" if msg["role"] == "user" else "🌌"
    with st.chat_message(msg["role"], avatar=avatar):
        if msg["content"]: st.markdown(msg["content"])
        if msg.get("image"): st.image(msg["image"], width=300)
        if msg.get("audio"):
            aud_id = f"aud_{i}"
            html = f"""<html><body style='margin:0;'><audio id='{aud_id}' src='data:audio/mp3;base64,{msg['audio']}'></audio>
            <button onclick="var a=document.getElementById('{aud_id}'); if(a.paused){{a.play();this.innerHTML='⏸️';}}else{{a.pause();this.innerHTML='▶️';}}" 
            style='background:#30363d;border:1px solid #8b949e;color:white;padding:5px 15px;border-radius:20px;cursor:pointer;'>▶️ Escuchar</button>
            <script>document.getElementById('{aud_id}').onended=function(){{this.nextElementSibling.innerHTML='▶️';}}</script></body></html>"""
            components.html(html, height=45)

# Input del chat
if prompt := st.chat_input("Escribe o sube una imagen...", accept_file=True, file_type=["jpg","png","jpeg"]):
    img_b64 = None
    if prompt.files:
        from PIL import Image
        img = Image.open(prompt.files[0])
        buf = io.BytesIO()
        img.save(buf, format=img.format if img.format else "PNG")
        img_b64 = base64.b64encode(buf.getvalue()).decode()
        img_b64 = f"data:image/{img.format.lower()};base64,{img_b64}"

    st.session_state.messages.append({"role": "user", "content": prompt.text, "image": img_b64})
    st.rerun()

# Respuesta de la IA (si el último mensaje es del usuario)
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant", avatar="🌌"):
        with st.spinner("Maya está pensando..."):
            historial = [{"role": "system", "content": SYSTEM_PROMPT}]
            for m in st.session_state.messages:
                content = m["content"]
                if m.get("image"):
                    content = [{"type": "text", "text": m["content"] or "Analiza esta imagen"},
                               {"type": "image_url", "image_url": {"url": m["image"]}}]
                historial.append({"role": m["role"], "content": content})

            try:
                # MOTOR LLAMA 3.2 INSTRUCT (Estable y con visión)
                res = cliente_ia.chat.completions.create(model="llama-3.2-90b-vision-instruct", messages=historial)
                txt = res.choices[0].message.content
                st.markdown(txt)

                # VOZ ELEVENLABS
                aud_final = None
                try:
                    v_url = "https://api.elevenlabs.io/v1/text-to-speech/EXAVITQu4vr4xnSDxMaL"
                    v_head = {"xi-api-key": MI_LLAVE_ELEVENLABS, "Content-Type": "application/json"}
                    v_data = {"text": txt.replace("*",""), "model_id": "eleven_multilingual_v2"}
                    v_res = requests.post(v_url, json=v_data, headers=v_head)
                    if v_res.status_code == 200:
                        aud_final = base64.b64encode(v_res.content).decode()
                except: pass

                st.session_state.messages.append({"role": "assistant", "content": txt, "audio": aud_final})
                guardar_memoria()
                st.rerun()
            except Exception as e:
                st.error(f"🚨 Error: {e}")