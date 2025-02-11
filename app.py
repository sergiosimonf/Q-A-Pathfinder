import os
import time
import json
import requests
import streamlit as st
import uuid  # Importamos para generar claves únicas

# ===============================
# Constantes y configuración
# ===============================

SUBSCRIPTION_KEY = st.secrets["SUBSCRIPTION_KEY"]
BASE_URL = st.secrets["BASE_URL"]
PROJECT_NAME = st.secrets["PROJECT_NAME"]
API_VERSION = st.secrets["API_VERSION"]
DEPLOYMENT_NAME = st.secrets["DEPLOYMENT_NAME"]

HEADERS = {
    "Ocp-Apim-Subscription-Key": SUBSCRIPTION_KEY,
    "Content-Type": "application/json"
}

# ===============================
# Inicialización de session_state
# ===============================
if "messages" not in st.session_state:
    st.session_state.messages = []

# Para almacenar temporalmente los prompts generados en la respuesta actual
if "current_prompts" not in st.session_state:
    st.session_state.current_prompts = {}

# Ocultar el menú, header y footer de Streamlit
st.markdown(
    """
    <style>
        #MainMenu, footer, header {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True
)

# ===============================
# Funciones auxiliares
# ===============================
def get_prompt_buttons(prompts: dict) -> None:
    """
    Muestra los botones de sugerencias (prompts) dentro del mensaje del asistente.

    Args:
        prompts (dict): Diccionario con 'display_texts' y 'prompts_dict'.
    """
    display_texts = prompts.get("display_texts", [])
    prompts_dict = prompts.get("prompts_dict", {})

    if display_texts:
        cols = st.columns(len(display_texts))
        for idx, display_text in enumerate(display_texts):
            with cols[idx]:
                unique_key = f"btn_{display_text}_{uuid.uuid4()}"  # Clave totalmente única
                st.button(
                    display_text,
                    key=unique_key,
                    on_click=handle_button_click,
                    args=(prompts_dict.get(display_text),)
                )

def update_prompts_from_data(answer_data: dict) -> dict:
    """
    A partir de la respuesta de la API, extrae y retorna los prompts disponibles.

    Args:
        answer_data (dict): Diccionario con la respuesta de la API.
    Returns:
        dict: Diccionario con 'display_texts' y 'prompts_dict'. Si no hay prompts, se retorna un dict vacío.
    """
    prompts = answer_data.get("dialog", {}).get("prompts", [])
    if prompts:
        display_texts = [prompt["displayText"] for prompt in prompts]
        prompts_dict = {prompt["displayText"]: prompt["qnaId"] for prompt in prompts}
        return {"display_texts": display_texts, "prompts_dict": prompts_dict}
    return {}

# ===============================
# Funciones para comunicación con la API
# ===============================
def response_generator_qna_id(qna_id: str) -> dict:
    """
    Consulta la API utilizando un qnaId específico.

    Args:
        qna_id (str): Identificador del QnA.
    Returns:
        dict: Respuesta en formato JSON.
    """
    url = f"{BASE_URL}?projectName={PROJECT_NAME}&api-version={API_VERSION}&deploymentName={DEPLOYMENT_NAME}"
    payload = json.dumps({
        "qnaId": qna_id,
        "top": 1,
        "userId": "Default",
        "isTest": False
    })

    try:
        response = requests.post(url, data=payload, headers=HEADERS)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error en la petición QnAId: {e}")
        return {}

def response_generator(question: str) -> str:
    """
    Consulta la base de conocimientos con la pregunta del usuario y retorna la respuesta.

    Args:
        question (str): Pregunta ingresada por el usuario.
    Returns:
        str: Texto de la respuesta del asistente.
    """
    url = f"{BASE_URL}?projectName={PROJECT_NAME}&api-version={API_VERSION}&deploymentName={DEPLOYMENT_NAME}"
    payload = {
        "top": 3,
        "question": question,
        "includeUnstructuredSources": True,
        "confidenceScoreThreshold": "0.5",
        "answerSpanRequest": {
            "enable": True,
            "topAnswersWithSpan": 1,
            "confidenceScoreThreshold": "0.5"
        }
    }

    try:
        response = requests.post(url, json=payload, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        answers = data.get("answers", [])
        if not answers:
            return "No se encontró respuesta."
        answer_data = answers[0]
        # Actualizar y almacenar los prompts generados para esta respuesta.
        st.session_state.current_prompts = update_prompts_from_data(answer_data)
        return answer_data.get("answer", "No se encontró respuesta.")
    except requests.exceptions.RequestException as e:
        return f"Error en la petición: {e}"

# ===============================
# Función para manejar el clic en un botón de prompt
# ===============================
def handle_button_click(qna_id: str) -> None:
    """
    Maneja el clic en un botón de prompt, consulta la API y actualiza el historial de mensajes.

    Args:
        qna_id (str): qnaId asociado al botón clickeado.
    """
    data = response_generator_qna_id(qna_id)
    if not data:
        return

    answers = data.get("answers", [])
    if not answers:
        st.session_state.messages.append({
            "role": "assistant", "content": "No se encontró respuesta."
        })
        return

    answer_data = answers[0]
    # Se extrae la primera pregunta asociada para mostrarla como mensaje del usuario.
    question_text = answer_data.get("questions", ["Consulta adicional"])[0]
    st.session_state.messages.append({"role": "user", "content": question_text})
    time.sleep(0.3)
    answer_text = answer_data.get("answer", "No se encontró respuesta.")
    prompts = update_prompts_from_data(answer_data)
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer_text,
        "prompts": prompts
    })

# ===============================
# Interfaz de usuario con Streamlit
# ===============================
st.title("Pathfinder 2e QnA Chatbot")

# Mostrar el historial de mensajes
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        # Si el mensaje del asistente tiene prompts, se muestran dentro del mismo bloque.
        if message["role"] == "assistant" and message.get("prompts"):
            get_prompt_buttons(message["prompts"])

# Manejo de la entrada del usuario
if user_input := st.chat_input("Envía un mensaje..."):
    # Agregar mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Procesar respuesta del asistente y mostrarla junto con sus prompts (si hay)
    with st.chat_message("assistant"):
        with st.spinner("Consultando la base de conocimientos..."):
            final_response = response_generator(user_input)
            st.markdown(final_response)
        # Obtener los prompts generados en la respuesta
        prompts = st.session_state.get("current_prompts", {})
        if prompts:
            get_prompt_buttons(prompts)

    # Agregar el mensaje del asistente (con sus prompts) al historial
    st.session_state.messages.append({
        "role": "assistant",
        "content": final_response,
        "prompts": st.session_state.get("current_prompts", {})
    })