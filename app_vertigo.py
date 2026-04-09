import streamlit as st
import json
import requests
import re
from datetime import datetime
from openai import OpenAI
import io
import base64
import streamlit.components.v1 as components

# --- 1. CONFIGURACIÓN ---
MI_LLAVE_OPENAI = st.secrets["MI_LLAVE_OPENAI"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
MI_LLAVE_ELEVENLABS = st.secrets["MI_LLAVE_ELEVENLABS"]

# Conectamos directo a OpenAI (Cerebro de ChatGPT)
cliente_ia = OpenAI(api_key=MI_LLAVE_OPENAI)

headers = {
    "apikey": SUPABASE_KEY, 
    "Authorization": f"Bearer {SUPABASE_KEY}", 
    "Content-Type": "application/json", 
    "Prefer": "resolution=merge-duplicates"
}

st.set_page_config(page_title="Maya | IxInteractive", page_icon="🌌")
st.markdown("<style>.stApp { background-color: #0d1117; color: #c9d1d9; } .stChatMessage { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 15px; margin-bottom: 10px; }</style>", unsafe_allow_html=True)

# --- 2. ACCESO ---
if "usuario_id" not in st.session_state:
    st.title("🏢 IxInteractive Studios")
    st.subheader("Acceso a Maya AI")
    with st.form("login_form"):
        correo_input = st.text_input("✉️ Correo:", placeholder="tu@correo.com")
        if st.form_submit_button("Entrar", use_container_width=True):
            if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', correo_input.strip()):
                st.session_state.usuario_id = correo_input.strip().lower()
                st.rerun()
            else: st.error("Correo inválido")
    st.stop()

# --- 3. MEMORIA ---
if "chat_actual" not in st.session_state:
    st.session_state.chat_actual = datetime.now().strftime("Chat_%Y%m%d_%H%M%S")
    st.session_state.messages = []

def guardar_memoria():
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chats"
    datos = {"id": st.session_state.chat_actual, "mensajes": st.session_state.messages, "usuario_id": st.session_state.usuario_id}
    try: requests.post(url, headers=headers, json=datos)
    except: pass

# --- 4. BARRA LATERAL ---
with st.sidebar:
    st.title("👤 Perfil")
    st.caption(f"Conectado: **{st.session_state.usuario_id}**")
    if st.button("🚪 Salir", use_container_width=True):
        st.session_state.clear()
        st.rerun()
    st.markdown("---")
    if st.button("➕ Nuevo Chat", use_container_width=True):
        st.session_state.chat_actual = datetime.now().strftime("Chat_%Y%m%d_%H%M%S")
        st.session_state.messages = []
        st.rerun()
    st.markdown("---")
    st.subheader("Historial")
    try:
        url_get = f"{SUPABASE_URL.rstrip('/')}/rest/v1/chats"
        r = requests.get(url_get, headers=headers, params={"usuario_id": f"eq.{st.session_state.usuario_id}", "select": "id"})
        if r.status_code == 200:
            for c in sorted(r.json(), key=lambda x: x["id"], reverse=True):
                col1, col2 = st.columns([4,1])
                with col1:
                    if st.button(f"💬 {c['id'][:12]}", key=f"L_{c['id']}", use_container_width=True):
                        det = requests.get(url_get, headers=headers, params={"id": f"eq.{c['id']}", "select": "*"}).json()
                        st.session_state.chat_actual, st.session_state.messages = c['id'], det[0]['mensajes']
                        st.rerun()
                with col2:
                    if st.button("❌", key=f"D_{c['id']}"):
                        requests.delete(url_get, headers=headers, params={"id": f"eq.{c['id']}"})
                        st.rerun()
    except: pass

# --- 5. CHAT PRINCIPAL ---
st.title("Hola, soy Maya 🌌")
st.caption(f"IxInteractive Studios | ID: {st.session_state.chat_actual}")

for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🌌"):
        if msg["content"]: st.markdown(msg["content"])
        if msg.get("image"): st.image(msg["image"], width=300)
        if msg.get("audio"):
            aud_id = f"aud_{i}"
            html = f"""<html><body style='margin:0; background:transparent;'><audio id='{aud_id}' src='data:audio/mp3;base64,{msg['audio']}'></audio>
            <button onclick="var a=document.getElementById('{aud_id}'); if(a.paused){{a.play();this.innerHTML='⏸️ Pausar';}}else{{a.pause();this.innerHTML='▶️ Escuchar';}}" 
            style='background:#30363d;border:1px solid #8b949e;color:white;padding:5px 15px;border-radius:20px;cursor:pointer;font-family:sans-serif;font-size:12px;'>▶️ Escuchar</button>
            <script>document.getElementById('{aud_id}').onended=function(){{this.nextElementSibling.innerHTML='▶️ Escuchar';}}</script></body></html>"""
            components.html(html, height=45)

if prompt := st.chat_input("Escribe o sube una imagen...", accept_file=True, file_type=["jpg","png","jpeg"]):
    img_url = None
    if prompt.files:
        from PIL import Image
        img = Image.open(prompt.files[0])
        buf = io.BytesIO()
        img.save(buf, format=img.format if img.format else "PNG")
        img_url = f"data:image/{img.format.lower() if img.format else 'png'};base64,{base64.b64encode(buf.getvalue()).decode()}"
    
    st.session_state.messages.append({"role": "user", "content": prompt.text, "image": img_url})
    st.rerun()

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant", avatar="🌌"):
        with st.spinner("Maya pensando..."):
            sys_msg = "Eres Maya, una IA femenina y profesional de IxInteractive Studios. Resuelve con claridad. No menciones nombres internos."
            hist = [{"role": "system", "content": sys_msg}]
            for m in st.session_state.messages:
                content = [{"type": "text", "text": m["content"] or "Analiza esto"}]
                if m.get("image"):
                    content.append({"type": "image_url", "image_url": {"url": m["image"]}})
                hist.append({"role": m["role"], "content": content})

            try:
                # MOTOR ESTABLE: GPT-4o-mini
                res = cliente_ia.chat.completions.create(model="gpt-4o-mini", messages=hist)
                txt = res.choices[0].message.content
                st.markdown(txt)

                aud_b64 = None
                try:
                    v_url = f"https://api.elevenlabs.io/v1/text-to-speech/EXAVITQu4vr4xnSDxMaL"
                    v_res = requests.post(v_url, 
                        json={"text": txt.replace("*",""), "model_id": "eleven_multilingual_v2"}, 
                        headers={"xi-api-key": MI_LLAVE_ELEVENLABS, "Content-Type": "application/json"})
                    if v_res.status_code == 200: aud_b64 = base64.b64encode(v_res.content).decode()
                except: pass

                st.session_state.messages.append({"role": "assistant", "content": txt, "audio": aud_b64})
                guardar_memoria()
                st.rerun()
            except Exception as e: st.error(f"🚨 Error: {e}")