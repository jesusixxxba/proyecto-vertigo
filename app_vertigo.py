import streamlit as st
import json
import requests
import re
from datetime import datetime
from groq import Groq
from streamlit_mic_recorder import mic_recorder # <--- Nuevos oídos

# ===================== 1. CONFIGURACIÓN =====================
MI_LLAVE_GROQ = st.secrets["MI_LLAVE_GROQ"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

cliente_groq = Groq(api_key=MI_LLAVE_GROQ)

st.set_page_config(page_title="Maya AI", page_icon="🌌", layout="centered")

# ===================== 2. ESTÉTICA Y VOZ (JS) =====================
st.markdown("""
    <style>
    .stApp { background: radial-gradient(circle at top right, #1a1f2e, #0d1117); color: #c9d1d9; }
    [data-testid="stChatMessage"] { background: rgba(22, 27, 34, 0.6) !important; backdrop-filter: blur(8px); border-radius: 16px !important; }
    /* Estilo para el botón del micro */
    .mic-container { display: flex; justify-content: center; margin-bottom: 10px; }
    </style>
    
    <script>
    function leerEnVozAlta(texto) {
        const mensaje = new SpeechSynthesisUtterance(texto);
        mensaje.lang = 'es-MX'; // Voz en español
        mensaje.rate = 1.1;     // Velocidad ligeramente más humana
        window.speechSynthesis.speak(mensaje);
    }
    </script>
    """, unsafe_allow_html=True)

# Función para disparar la voz desde Python
def maya_habla(texto):
    texto_limpio = texto.replace('"', "'").replace("\n", " ")
    st.markdown(f"""<script>leerEnVozAlta("{texto_limpio}")</script>""", unsafe_allow_html=True)

# ===================== 3. ACCESO Y LÓGICA =====================
# (Mantener aquí tu código de login y Supabase igual que antes)
if "messages" not in st.session_state: st.session_state.messages = []

# ===================== 4. INTERFAZ DE VOZ Y TEXTO =====================
st.markdown('<h1 style="text-align:center;">Maya AI 🌌</h1>', unsafe_allow_html=True)

# --- EL MICRÓFONO ---
st.write("---")
st.markdown('<p style="text-align:center; color:#8b949e;">Pulsa para hablar con Maya</p>', unsafe_allow_html=True)
col_mic, _ = st.columns([1, 4])
with col_mic:
    audio = mic_recorder(start_prompt="🎤 Hablar", stop_prompt="🛑 Detener", key="mic")

# Dibujar historial
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="👤" if msg["role"]=="user" else "🌌"):
        st.markdown(msg["content"])

# --- PROCESAR ENTRADA (VOZ O TEXTO) ---
input_usuario = None

# Si el usuario usó el micro
if audio:
    # Aquí usamos el motor Whisper de Groq para convertir audio a texto (STT)
    # Nota: requiere guardar el audio temporalmente o enviarlo como bytes
    st.info("Maya está transcribiendo tu voz...")
    # Por ahora, para la Beta, podemos usar la transcripción nativa si tu sistema lo permite
    # o integrar el modelo Whisper de Groq aquí.

# Si el usuario escribe
if prompt := st.chat_input("Escribe una instrucción..."):
    input_usuario = prompt

if input_usuario:
    st.session_state.messages.append({"role": "user", "content": input_usuario})
    st.rerun()

# Respuesta de Maya
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant", avatar="🌌"):
        with st.spinner("Maya procesando..."):
            try:
                hist = [{"role": "system", "content": "Eres Maya. Responde de forma breve para que la lectura de voz sea fluida."}] + st.session_state.messages
                res = cliente_groq.chat.completions.create(messages=hist, model="llama-3.3-70b-versatile")
                txt = res.choices[0].message.content
                
                st.markdown(txt)
                st.session_state.messages.append({"role": "assistant", "content": txt})
                
                # ¡MAYA HABLA!
                maya_habla(txt)
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")