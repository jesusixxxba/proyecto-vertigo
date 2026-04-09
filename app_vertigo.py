import streamlit as st
import requests
import re
from datetime import datetime
from openai import OpenAI
import io
import base64
import streamlit.components.v1 as components
from PIL import Image

# --- 1. CONFIGURACIÓN DE LLAVES ---
MI_LLAVE_GROQ = st.secrets["MI_LLAVE_GROQ"]
MI_LLAVE_GEMINI = st.secrets["MI_LLAVE_GEMINI"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
MI_LLAVE_ELEVENLABS = st.secrets["MI_LLAVE_ELEVENLABS"]

# Clientes de IA
cliente_groq = OpenAI(api_key=MI_LLAVE_GROQ, base_url="https://api.groq.com/openai/v1")
cliente_gemini = OpenAI(api_key=MI_LLAVE_GEMINI, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates"
}

st.set_page_config(page_title="Maya | IxInteractive", page_icon="🌌", layout="centered")

# Estilo moderno oscuro
st.markdown("""
<style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    .stChatMessage { 
        background-color: #161b22; 
        border: 1px solid #30363d; 
        border-radius: 12px; 
        padding: 16px; 
        margin-bottom: 12px; 
    }
    .stChatMessage.user { border-left: 4px solid #58a6ff; }
    .stChatMessage.assistant { border-left: 4px solid #a5d6ff; }
</style>
""", unsafe_allow_html=True)

# --- 2. ACCESO SIMPLE POR CORREO ---
if "usuario_id" not in st.session_state:
    st.title("🏢 IxInteractive Studios")
    st.subheader("Acceso a Maya AI")
    with st.form("login"):
        correo = st.text_input("✉️ Ingresa tu correo:", placeholder="tu@correo.com")
        if st.form_submit_button("Entrar a Maya"):
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

# --- 3. BARRA LATERAL ---
with st.sidebar:
    st.title("👤 Perfil")
    st.caption(f"Usuario: {st.session_state.usuario_id}")
    
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
st.caption("Tu asistente de roleplay e IxInteractive Studios")

# Mostrar historial de mensajes
for i, msg in enumerate(st.session_state.messages):
    avatar = "👤" if msg["role"] == "user" else "🌌"
    with st.chat_message(msg["role"], avatar=avatar):
        if msg.get("content"):
            st.markdown(msg["content"])
        if msg.get("image"):
            st.image(msg["image"], width=320)
        
        # Botón de audio mejorado
        if msg.get("audio"):
            audio_html = f"""
            <div style="margin: 10px 0;">
                <audio id="aud_{i}" src="data:audio/mp3;base64,{msg['audio']}"></audio>
                <button onclick="var a = document.getElementById('aud_{i}'); 
                if(a.paused){{a.play(); this.textContent='⏸️ Pausar';}} 
                else {{a.pause(); this.textContent='▶️ Escuchar';}}" 
                style="background:#21262d; color:white; border:1px solid #8b949e; padding:8px 18px; 
                border-radius:20px; cursor:pointer; font-size:14px;">
                ▶️ Escuchar
                </button>
            </div>
            """
            components.html(audio_html, height=55)

# --- ENTRADA DEL USUARIO ---
if prompt := st.chat_input("Escribe tu mensaje o sube una imagen...", accept_file=True, file_type=["jpg", "png", "jpeg"]):
    img_url = None
    texto_usuario = prompt.text if hasattr(prompt, "text") else str(prompt)

    if prompt.files:
        try:
            img = Image.open(prompt.files[0])
            buf = io.BytesIO()
            img.save(buf, format=img.format or "PNG")
            img_url = f"data:image/{(img.format or 'png').lower()};base64,{base64.b64encode(buf.getvalue()).decode()}"
        except:
            st.error("No se pudo procesar la imagen")

    st.session_state.messages.append({
        "role": "user",
        "content": texto_usuario,
        "image": img_url
    })
    st.rerun()

# --- LÓGICA DE RESPUESTA CON FALLBACK ---
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant", avatar="🌌"):
        with st.spinner("Maya está pensando..."):
            # System Prompt mejorado
            system_prompt = """
            Eres Maya, una IA cálida, inteligente y creativa de IxInteractive Studios.
            Especializada en roleplay inmersivo y apoyo a tiendas digitales.
            Habla de forma natural, amigable y profesional. Sé empática y entusiasta cuando corresponda.
            """

            # Construir historial
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

            # Modelos en orden de prioridad
            opciones = [
                {"cliente": cliente_groq, "modelo": "llama-3.3-70b-versatile"},
                {"cliente": cliente_groq, "modelo": "llama-3.1-8b-instant"},
                {"cliente": cliente_groq, "modelo": "llama-3.2-11b-vision-preview"},
                {"cliente": cliente_gemini, "modelo": "gemini-2.5-flash"},
                {"cliente": cliente_gemini, "modelo": "gemini-1.5-flash"},
            ]

            txt = None
            for opcion in opciones:
                try:
                    res = opcion["cliente"].chat.completions.create(
                        model=opcion["modelo"],
                        messages=hist,
                        temperature=0.75,
                        max_tokens=1100
                    )
                    txt = res.choices[0].message.content
                    break
                except:
                    continue

            if txt:
                st.markdown(txt)

                # === GENERACIÓN DE AUDIO CON ELEVENLABS ===
                aud_b64 = None
                try:
                    clean_text = txt.replace("**", "").replace("*", "").strip()
                    v_res = requests.post(
                        "https://api.elevenlabs.io/v1/text-to-speech/EXAVITQu4vr4xnSDxMaL",
                        json={
                            "text": clean_text,
                            "model_id": "eleven_multilingual_v2",
                            "voice_settings": {
                                "stability": 0.75,
                                "similarity_boost": 0.85,
                                "style": 0.1
                            }
                        },
                        headers={
                            "xi-api-key": MI_LLAVE_ELEVENLABS,
                            "Content-Type": "application/json"
                        },
                        timeout=12
                    )
                    
                    if v_res.status_code == 200:
                        aud_b64 = base64.b64encode(v_res.content).decode()
                    else:
                        st.caption("⚠️ Audio no disponible en este momento")
                except:
                    st.caption("⚠️ No se pudo generar el audio")

                # Guardar respuesta
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": txt,
                    "audio": aud_b64
                })
                guardar_memoria()
                st.rerun()

            else:
                st.error("🚨 No se pudo conectar con ningún modelo en este momento. Intenta de nuevo.")