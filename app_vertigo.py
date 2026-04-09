import streamlit as st
import requests
import re
from datetime import datetime
from openai import OpenAI
import io
import base64
import streamlit.components.v1 as components
from PIL import Image

# --- 1. CONFIGURACIÓN ---
MI_LLAVE_GROQ = st.secrets["MI_LLAVE_GROQ"]
MI_LLAVE_GEMINI = st.secrets["MI_LLAVE_GEMINI"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
MI_LLAVE_ELEVENLABS = st.secrets["MI_LLAVE_ELEVENLABS"]

cliente_groq = OpenAI(api_key=MI_LLAVE_GROQ, base_url="https://api.groq.com/openai/v1")
cliente_gemini = OpenAI(api_key=MI_LLAVE_GEMINI, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")

headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}

st.set_page_config(page_title="Maya | IxInteractive", page_icon="🌌", layout="centered")

# --- 2. ACCESO ---
if "usuario_id" not in st.session_state:
    st.title("🏢 IxInteractive Studios")
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

# --- 3. CHAT PRINCIPAL ---
st.title("Hola, soy Maya 🌌")

for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🌌"):
        if msg.get("content"): st.markdown(msg["content"])
        if msg.get("image"): st.image(msg["image"], width=320)
        
        if msg.get("audio"):
            aud_id = f"aud_{i}"
            audio_html = f"""
            <div style="margin: 10px 0;">
                <audio id="{aud_id}" src="data:audio/mp3;base64,{msg['audio']}"></audio>
                <button id="btn_{aud_id}" onclick="
                    var a = document.getElementById('{aud_id}');
                    var b = document.getElementById('btn_{aud_id}');
                    if(a.paused){{ a.play(); b.innerHTML = '⏸️ Pausar'; }} 
                    else {{ a.pause(); b.innerHTML = '▶️ Escuchar'; }}
                    a.onended = function(){{ b.innerHTML = '▶️ Escuchar'; }};
                " style="background:#21262d; color:white; border:1px solid #8b949e; padding:8px 20px; border-radius:20px; cursor:pointer;">
                ▶️ Escuchar
                </button>
            </div>
            """
            components.html(audio_html, height=50)

if prompt := st.chat_input("Escribe...", accept_file=True, file_type=["jpg", "png", "jpeg"]):
    img_url = None
    if prompt.files:
        img = Image.open(prompt.files[0])
        buf = io.BytesIO()
        img.save(buf, format=img.format or "PNG")
        img_url = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
    st.session_state.messages.append({"role": "user", "content": prompt.text if hasattr(prompt, "text") else str(prompt), "image": img_url})
    st.rerun()

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant", avatar="🌌"):
        with st.spinner("Maya pensando..."):
            hist = [{"role": "system", "content": "Eres Maya, una IA de IxInteractive Studios."}]
            for m in st.session_state.messages:
                content = [{"type": "text", "text": m.get("content", "Analiza esto")}]
                if m.get("image"): content.append({"type": "image_url", "image_url": {"url": m["image"]}})
                hist.append({"role": m["role"], "content": content})

            # TUS MODELOS EXACTOS
            opciones = [
                {"cliente": cliente_groq, "modelo": "llama-3.3-70b-versatile"},
                {"cliente": cliente_groq, "modelo": "llama-3.2-11b-vision-preview"},
                {"cliente": cliente_gemini, "modelo": "gemini-2.5-flash"},
            ]

            txt = None
            for opcion in opciones:
                try:
                    res = opcion["cliente"].chat.completions.create(model=opcion["modelo"], messages=hist)
                    txt = res.choices[0].message.content
                    break
                except Exception as e:
                    if "401" in str(e): st.error("🚨 Error 401 en el Motor de IA: Tu llave de Groq o Gemini es incorrecta.")
                    continue

            if txt:
                st.markdown(txt)
                aud_b64 = None
                try:
                    clean_text = txt.replace("*", "").strip()
                    v_res = requests.post(
                        "https://api.elevenlabs.io/v1/text-to-speech/EXAVITQu4vr4xnSDxMaL",
                        json={"text": clean_text, "model_id": "eleven_multilingual_v2"},
                        headers={"xi-api-key": MI_LLAVE_ELEVENLABS.strip(), "Content-Type": "application/json"}
                    )
                    if v_res.status_code == 200:
                        aud_b64 = base64.b64encode(v_res.content).decode()
                    elif v_res.status_code == 401:
                        st.warning("🔑 La llave de ElevenLabs no fue aceptada (Error 401).")
                except: pass

                st.session_state.messages.append({"role": "assistant", "content": txt, "audio": aud_b64})
                st.rerun()