import streamlit as st
import os
import json
import re
from groq import Groq

# --- IMPORTAMOS TU BASE DE DATOS ESTRUCTURADA ---
# Asegúrate de que el archivo datos_anmi.py esté en la misma carpeta
from datos_anmi import CONOCIMIENTO_ESTRUCTURADO

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="ANMI - Chatbot", page_icon="🛡️")



st.title("🛡️ ANMI: Lucha contra la Anemia")
st.caption("Asistente Nutricional Materno Infantil (IA Supervisada)")



# --- INICIALIZACIÓN DE ESTADO ---
if "historial" not in st.session_state:
    st.session_state.historial = []
    mensaje_bienvenida = (
        "👋 ¡Hola! Soy ANMI.\n\n"
        "Soy un asistente educativo y **NO reemplazo a un médico**.\n\n"
       # ...
"Para comenzar, necesito que leas y aceptes los "
"términos y condiciones que verás aquí abajo 👇 " # <--- NUEVO TEXTO
"para tratar tus datos de forma anónima."
# ...
    )
    st.session_state.historial.append({"role": "assistant", "content": mensaje_bienvenida})

if "contexto" not in st.session_state:
    st.session_state.contexto = {"edad_bebe": None, "consentimiento": False, "fin_conversacion": False}


# --- CEREBRO INTELIGENTE (CON MEMORIA) ---
class AnmiBrain:
    def __init__(self):
        self.client = Groq(api_key=API_KEY)
        # Respuestas de control
        self.respuestas_control = {
            "rechazo": "Entendido. Respetamos tu privacidad. No podemos continuar sin consentimiento. 🔒",
            "pedir_edad": "¡Gracias por aceptar! ✅\n\nPara darte la mejor información, selecciona la **edad de tu bebé** en meses:",
            "urgencia": "🚨 **¡ALERTA DE EMERGENCIA!**\n\nLo que describes parece una urgencia médica.\n\n**ACCIÓN:** Acude INMEDIATAMENTE al centro de salud.\n\n**GENERAL:** 119\n\n**ESSALUD:** 117\n\n**SAMU:** 106\n\nEl bot se ha detenido por seguridad.",
            "fuera_rango": "⚠️ ANMI está diseñado para bebés de 6 a 12 meses. Consulta a tu pediatra."
        }

    def consultar_experto(self, consulta_usuario, edad_bebe, historial_chat):
        # Determinamos si es un bebé menor de 6 meses para activar el "Modo Lactancia"
        es_menor_de_6_meses = False
        try:
            # Si edad_bebe es un número (int o float) y es menor a 6
            if isinstance(edad_bebe, (int, float)) and edad_bebe < 6:
                es_menor_de_6_meses = True
        except:
            pass

        # 1. Definimos el Prompt del Sistema con REGLAS DE SEGURIDAD
        prompt_sistema = f"""
        Eres ANMI, un experto en nutrición infantil del Ministerio de Salud del Perú.
        
        TU OBJETIVO:
        Responder a la madre/padre basándote ÚNICAMENTE en la siguiente INFORMACIÓN VALIDADA.

        --- INFORMACIÓN VALIDADA ---
        {CONOCIMIENTO_ESTRUCTURADO}
        ----------------------------

        DATOS DEL USUARIO:
        - El bebé tiene: {edad_bebe} meses.

        REGLAS FUNDAMENTALES:
        1. REGLA DE ORO (< 6 MESES): Si el bebé tiene MENOS de 6 meses, la alimentación es SOLO LACTANCIA MATERNA EXCLUSIVA.
           - Si te piden recetas o comidas (sangrecita, papillas, agua), NIEGATE amablemente y explica que su estómago no está listo.
           - Menciona la suplementación de hierro (gotitas) solo si corresponde a su edad (4 meses en adelante), según tus datos.
        
        2. Si el bebé tiene 6 meses o más, usa el recetario (Sangrecita, Bazo, Quinua) para dar recomendaciones.
        3. Usa el contexto de la conversación.
        4. Sé amable, empático y usa emojis.
        5. No inventes información que no esté en el texto validado.
        """

        # 2. CONSTRUIMOS LA MEMORIA PARA LA IA
        mensajes_para_ia = [{"role": "system", "content": prompt_sistema}]

        for mensaje in historial_chat:
            if mensaje["content"]:
                mensajes_para_ia.append({"role": mensaje["role"], "content": mensaje["content"]})

        try:
            chat = self.client.chat.completions.create(
                messages=mensajes_para_ia,
                model="llama-3.1-8b-instant",
                temperature=0.1
            )
            return chat.choices[0].message.content
        except Exception as e:
            return f"Tuve un problema de conexión: {str(e)}"


brain = AnmiBrain()

# --- INTERFAZ GRÁFICA ---

# 1. MOSTRAR HISTORIAL
for mensaje in st.session_state.historial:
    with st.chat_message(mensaje["role"]):
        st.markdown(mensaje["content"])

# 2. GESTIÓN DE ESTADOS

# CASO A: Consentimiento
if not st.session_state.contexto["consentimiento"] and not st.session_state.contexto["fin_conversacion"]:
    st.write("---")
    # --- AGREGA ESTO AQUÍ ---
    # Asegúrate de que la ruta 'views/terminos.py' sea correcta en tu carpeta
    st.page_link("pages/terminos_condiciones.py", label="📄 Leer Términos y Condiciones", icon="⚖️")
    st.write("") # Un pequeño espacio
    # ------------------------
    col1, col2 = st.columns(2)
    if col1.button("✅ SÍ, ACEPTO", use_container_width=True):
        st.session_state.contexto["consentimiento"] = True
        st.session_state.historial.append({"role": "user", "content": "✅ Sí, acepto."})
        # Cambiamos el mensaje para pedir la edad por escrito
        st.session_state.historial.append({"role": "assistant", "content": "¡Gracias por aceptar! ✅\n\nPara poder ayudarte mejor, por favor **escribe en el chat cuántos meses tiene tu bebé** (ejemplo: 8 meses)."})
        st.rerun()
    if col2.button("❌ NO ACEPTO", use_container_width=True):
        st.session_state.contexto["fin_conversacion"] = True
        st.session_state.historial.append({"role": "user", "content": "❌ No acepto."})
        st.session_state.historial.append({"role": "assistant", "content": brain.respuestas_control["rechazo"]})
        st.rerun()

# CASO B: Detección de Edad y Preguntas Generales
elif st.session_state.contexto["consentimiento"] and st.session_state.contexto["edad_bebe"] is None and not st.session_state.contexto["fin_conversacion"]:
    
    if prompt := st.chat_input("Escribe la edad de tu bebé o haz una pregunta..."):
        
        # 1. Mostrar mensaje del usuario
        st.session_state.historial.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 2. Intentar detectar una edad (ej: "8 meses", "1 año", "12 semanas")
        match = re.search(r'(\d+)\s*(d[ií]a|semana|mes|a[nñ]o)?', prompt, re.IGNORECASE)
        
        # --- OPCIÓN 1: EL USUARIO ESCRIBIÓ UNA EDAD ---
        if match:
            numero = int(match.group(1))
            unidad = match.group(2) if match.group(2) else "mes"
            unidad = unidad.lower()

            # Conversión a MESES
            edad_en_meses = 0
            texto_detectado = ""
            
            if "d" in unidad:    edad_en_meses = numero / 30; texto_detectado = f"{numero} días"
            elif "sem" in unidad:edad_en_meses = numero / 4;  texto_detectado = f"{numero} semanas"
            elif "a" in unidad:  edad_en_meses = numero * 12; texto_detectado = f"{numero} año(s)"
            else:                edad_en_meses = numero;      texto_detectado = f"{numero} meses"
            
            edad_en_meses = round(edad_en_meses, 1)

            # Validación de rango (0 a 36 meses)
            if 0 <= edad_en_meses <= 36:
                st.session_state.contexto["edad_bebe"] = edad_en_meses
                
                # Contexto específico para la IA
                prompt_sistema = f"[SISTEMA: El usuario indicó {texto_detectado} ({edad_en_meses} meses). Responde su consulta considerando esta edad exacta.] {prompt}"
                
                respuesta = brain.consultar_experto(prompt_sistema, edad_en_meses, st.session_state.historial)
                
                st.session_state.historial.append({"role": "assistant", "content": respuesta})
                with st.chat_message("assistant"):
                    st.markdown(respuesta)
                st.rerun()
            else:
                msg = f"⚠️ Has indicado **{texto_detectado}**. ANMI está diseñado para niños de 0 a 3 años. Consulta a un especialista."
                st.session_state.historial.append({"role": "assistant", "content": msg})
                with st.chat_message("assistant"):
                    st.markdown(msg)

        # --- OPCIÓN 2: EL USUARIO HIZO UNA PREGUNTA GENERAL (Sin números) ---
        else:
            # Asumimos que es una pregunta general (ej: "¿Qué es la anemia?")
            # Configuramos la edad como "General" para salir del bloqueo
            st.session_state.contexto["edad_bebe"] = "General"
            
            prompt_sistema = f"[SISTEMA: El usuario NO especificó edad todavía. Responde la duda de forma general. Si la respuesta depende de la edad, avísale.] {prompt}"
            
            respuesta = brain.consultar_experto(prompt_sistema, "No especificada (General)", st.session_state.historial)
            
            st.session_state.historial.append({"role": "assistant", "content": respuesta})
            with st.chat_message("assistant"):
                st.markdown(respuesta)
            st.rerun()
# 3. CHAT LIBRE (CON LA INTELIGENCIA CARGADA)
elif not st.session_state.contexto["fin_conversacion"]:
    if prompt := st.chat_input("Pregunta sobre anemia, recetas o suplementos..."):

        # A. Guardamos tu pregunta en el historial PRIMERO
        st.session_state.historial.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        # B. Filtro de seguridad
        if any(x in prompt.lower() for x in ["no respira", "se ahoga", "piel azul", "convulsion", "desmayo", "sangrado", "hemorragia"]):
            respuesta = brain.respuestas_control["urgencia"]
            st.session_state.contexto["fin_conversacion"] = True
        else:
            # C. CONSULTA INTELIGENTE CON MEMORIA
            edad = st.session_state.contexto["edad_bebe"]
            historial_completo = st.session_state.historial

            respuesta = brain.consultar_experto(prompt, edad, historial_completo)

        # D. Guardamos la respuesta y la mostramos
        st.session_state.historial.append({"role": "assistant", "content": respuesta})
        with st.chat_message("assistant"):
            st.markdown(respuesta)

        if st.session_state.contexto.get("fin_conversacion"):
            st.rerun()

else:

    st.error("La conversación ha terminado. Recarga la página (F5) para reiniciar.")

