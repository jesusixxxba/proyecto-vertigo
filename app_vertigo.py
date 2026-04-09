import streamlit as st
import json
import requests
import re
from datetime import datetime
from openai import OpenAI
import io
import base64
import streamlit.components.v1 as components

# --- 1. CONFIGURACIÓN DE LLAVES ---
MI_LLAVE_GROQ = st.secrets["MI_LLAVE_GROQ"]
MI_LLAVE_GEMINI = st.secrets["MI_LLAVE_GEMINI"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
MI_LLAVE_ELEVENLABS = st.secrets["MI_LLAVE_ELEVENLABS"]

# Creamos los dos clientes (Groq y Gemini)
cliente_groq = OpenAI(api_key=MI_LLAVE_GROQ, base_url="https://api.groq.com/openai/v1")
cliente_gemini = OpenAI(api_key=MI_LLAVE_GEMINI, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")

headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates"}

st.set_page_config(page_title="Maya | IxInteractive", page_icon="🌌")
st.markdown("<style>.stApp { background-color: #0d1117; color: #c9d1d9; } .stChatMessage { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 15px; margin-bottom: 10px; }</style>", unsafe_allow_html=True)

# --- 2. ACCESO Y MEMORIA ---
if "usuario_id" not in st.session_state:
    st.title("🏢 IxInteractive Studios")
    st.subheader("Acceso a Maya AI")
    with st.form("login"):
        correo = st.text_input("✉️ Correo:", placeholder="tu@correo.com")
        if st.form_submit_button("Entrar"):
            if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', correo.strip()):
                st.session_state.usuario_id = correo.strip().lower()
                st.rerun()
    st.stop()

if "chat_actual" not in st.session_state:
    st.session_state.chat_actual = datetime.now().strftime("Chat_%Y%m%d_%H%M%S")
    st.session_state.messages = []

def guardar_memoria():
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chats"
    datos = {"id": st.session_state.chat_actual, "mensajes": st.session_state.messages, "usuario_id": st.session_state.usuario_id}
    try: requests.post(url, headers=headers, json=datos)
    except: pass

# --- 3. BARRA LATERAL ---
with st.sidebar:
    st.title("👤 Perfil")
    st.caption(f"ID: {st.session_state.usuario_id}")
    if st.button("🚪 Salir", use_container_width=True):
        st.session_state.clear()
        st.rerun()
    st.markdown("---")
    if st.button("➕ Nuevo Chat", use_container_width=True):
        st.session_state.chat_actual = datetime.now().strftime("Chat_%Y%m%d_%H%M%S")
        st.session_state.messages = []
        st.rerun()

# --- 4. CHAT PRINCIPAL ---
st.title("Hola, soy Maya 🌌")

for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🌌"):
        if msg["content"]: st.markdown(msg["content"])
        if msg.get("image"): st.image(msg["image"], width=300)
        if msg.get("audio"):
            html = f"""<html><body style='margin:0; background:transparent;'><audio id='aud_{i}' src='data:audio/mp3;base64,{msg['audio']}'></audio>
            <button onclick="var a=document.getElementById('aud_{i}'); if(a.paused){{a.play();this.innerHTML='⏸️';}}else{{a.pause();this.innerHTML='▶️';}}" 
            style='background:#30363d;border:1px solid #8b949e;color:white;padding:5px 15px;border-radius:20px;cursor:pointer;'>▶️ Escuchar</button></body></html>"""
            components.html(html, height=45)

if prompt := st.chat_input("Escribe o sube imagen...", accept_file=True, file_type=["jpg","png","jpeg"]):
    img_url = None
    if prompt.files:
        from PIL import Image
        img = Image.open(prompt.files[0])
        buf = io.BytesIO()
        img.save(buf, format=img.format if img.format else "PNG")
        img_url = f"data:image/{img.format.lower() if img.format else 'png'};base64,{base64.b64encode(buf.getvalue()).decode()}"
    st.session_state.messages.append({"role": "user", "content": prompt.text, "image": img_url})
    st.rerun()

# --- LÓGICA DE RESPUESTA CON FALLBACK ---
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant", avatar="🌌"):
        with st.spinner("Maya analizando..."):
            hist = [{"role": "system", "content": "Eres Maya, IA de IxInteractive Studios. Resuelve con claridad."}]
            for m in st.session_state.messages:
                content = [{"type": "text", "text": m["content"] or "Analiza esto"}]
                if m.get("image"): content.append({"type": "image_url", "image_url": {"url": m["image"]}})
                hist.append({"role": m["role"], "content": content})

            # LISTA DE CEREBROS (Intentará uno por uno si fallan)
            opciones = [
                {"cliente": cliente_groq, "modelo": "llama-3.2-90b-vision-preview"},
                {"cliente": cliente_groq, "modelo": "llama-3.2-11b-vision-preview"},
                {"cliente": cliente_gemini, "modelo": "gemini-1.5-flash"}
            ]

            txt = None
            for opcion in opciones:
                try:
                    res = opcion["cliente"].chat.completions.create(model=opcion["modelo"], messages=hist)
                    txt = res.choices[0].message.content
                    break # Si funciona, salimos del bucle
                except Exception as e:
                    continue # Si falla, intenta el siguiente

            if txt:
                st.markdown(txt)
                aud_b64 = None
                try:
                    v_res = requests.post("https://api.elevenlabs.io/v1/text-to-speech/EXAVITQu4vr4xnSDxMaL", 
                        json={"text": txt.replace("*",""), "model_id": "eleven_multilingual_v2"}, 
                        headers={"xi-api-key": MI_LLAVE_ELEVENLABS, "Content-Type": "application/json"})
                    if v_res.status_code == 200: aud_b64 = base64.b64encode(v_res.content).decode()
                except: pass
                st.session_state.messages.append({"role": "assistant", "content": txt, "audio": aud_b64})
                guardar_memoria()
                st.rerun()
            else:
                st.error("🚨 Todos los motores están fallando. Intenta de nuevo en un momento.")