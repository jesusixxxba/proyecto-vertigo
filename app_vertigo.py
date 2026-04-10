import streamlit as st
import json
import requests
import hashlib
from datetime import datetime
from groq import Groq
import google.generativeai as genai
from PIL import Image
import io

# ===================== 1. CONFIGURACIÓN DE MOTORES =====================
# Llaves desde Secrets
MI_LLAVE_GROQ = st.secrets["MI_LLAVE_GROQ"]
MI_LLAVE_GEMINI = st.secrets["MI_LLAVE_GEMINI"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

# Inicializar Clientes
cliente_groq = Groq(api_key=MI_LLAVE_GROQ)
genai.configure(api_key=MI_LLAVE_GEMINI)
modelo_vision = genai.GenerativeModel('gemini-1.5-flash') # Gemini 3 Flash (vía API)

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates"
}

# ===================== 2. CACHÉ Y PROCESAMIENTO =====================

def obtener_hash_imagen(imagen_bytes):
    """Genera una huella única para no analizar la misma imagen dos veces."""
    return hashlib.md5(imagen_bytes).hexdigest()

def preprocesar_imagen(archivo):
    """Redimensiona y comprime para ahorrar ancho de banda."""
    img = Image.open(archivo)
    # Redimensionar si es muy grande
    img.thumbnail((512, 512))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=70)
    return buf.getvalue()

def consultar_vision(imagen_bytes):
    """Gemini 3 Flash: Traduce imagen a texto corto."""
    try:
        # Prompt de optimización
        prompt_vision = "Describe esta imagen de forma técnica y breve (máx 50 palabras). Si es hardware, identifica componentes."
        # Preparar para Gemini
        contenido = [prompt_vision, {"mime_type": "image/jpeg", "data": imagen_bytes}]
        res = modelo_vision.generate_content(contenido)
        return res.text
    except Exception as e:
        return f"[Error de visión: {e}]"

# ===================== 3. LÓGICA DE MAYA (ROUTER) =====================

def maya_router(texto, imagen_archivo=None):
    """Decide el flujo según la entrada del usuario."""
    descripcion_visual = ""
    
    if imagen_archivo:
        # Paso 1: Preprocesar
        img_bytes = preprocesar_imagen(imagen_archivo)
        img_hash = obtener_hash_imagen(img_bytes)
        
        # Paso 2: Verificar Caché (Simplificado en session_state por ahora)
        if "cache_vision" not in st.session_state:
            st.session_state.cache_vision = {}
            
        if img_hash in st.session_state.cache_vision:
            descripcion_visual = st.session_state.cache_vision[img_hash]
            st.toast("Imagen recuperada de caché ⚡")
        else:
            with st.spinner("Maya está observando..."):
                descripcion_visual = consultar_vision(img_bytes)
                st.session_state.cache_vision[img_hash] = descripcion_visual
                st.toast("Análisis visual completado 👁️")

    # Paso 3: Construir Contexto para LLaMA
    prompt_final = texto
    if descripcion_visual:
        prompt_final = f"[CONTEXTO VISUAL: {descripcion_visual}]\n\nUsuario dice: {texto}"

    # Paso 4: Razonamiento con LLaMA 3.3
    try:
        historial = [{"role": "system", "content": "Eres Maya de IxInteractive. Sé directa, útil y técnica. Evita rodeos sentimentales."}]
        # Solo enviamos los últimos 5 mensajes para ahorrar tokens y mantener foco
        historial += st.session_state.messages[-5:] 
        historial.append({"role": "user", "content": prompt_final})
        
        res = cliente_groq.chat.completions.create(
            messages=historial,
            model="llama-3.3-70b-versatile",
            temperature=0.6, # Menos creatividad, más precisión
        )
        return res.choices[0].message.content
    except Exception as e:
        return f"🚨 Error en cerebro LLaMA: {e}"

# ===================== 4. INTERFAZ STREAMLIT =====================

st.title("Maya AI 🌌")
st.caption("IxInteractive Hybrid Intelligence")

# Subida de imagen (opcional)
with st.sidebar:
    st.subheader("🛠️ Panel de Entrada")
    archivo_subido = st.file_uploader("Subir imagen (Análisis)", type=['jpg','png','jpeg'])
    if st.button("Limpiar historial"):
        st.session_state.messages = []
        st.rerun()

# Mostrar Chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input de Usuario
if prompt := st.chat_input("¿En qué puedo ayudarte?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
        if archivo_subido:
            st.image(archivo_subido, width=200)

    # Respuesta Híbrida
    with st.chat_message("assistant"):
        respuesta = maya_router(prompt, archivo_subido)
        st.markdown(respuesta)
        st.session_state.messages.append({"role": "assistant", "content": respuesta})
        
        # Sincronizar con Supabase (Tu función ya existente)
        # guardar_memoria()