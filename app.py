import streamlit as st
import time
import requests
import json

# Estilos CSS para el chat
st.markdown(
    """
    <style>    
    /* Contenedor general de cada mensaje de chat */
    div[data-testid="stChatMessage"] {
        padding: 8px 16px;
        border-radius: 20px;
        margin: 10px 0;
        max-width: 80%;
        line-height: 1.5;
    }
    /* Estilo para mensajes del usuario */
    div[data-testid="stChatMessage"][data-is-user="true"] {
        background-color: #0084ff;
        color: #fff;
        align-self: flex-end;
        text-align: right;
    }
    /* Estilo para mensajes del asistente */
    div[data-testid="stChatMessage"][data-is-user="false"] {
        background-color: #e5e5ea;
        color: #000;
        align-self: flex-start;
        text-align: left;
    }
    /* Opcional: Personalizar el input del chat */
    div[data-testid="stChatInput"] input {
        border: none;
        border-radius: 20px;
        padding: 10px 20px;
        font-size: 16px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    #MainMenu, footer, header {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True
)

def response_generator(question: str):
    reqUrl = "https://tradicionalia.cognitiveservices.azure.com/language/:query-knowledgebases?projectName=PathfinderFaQ&api-version=2021-10-01&deploymentName=production"
    headersList = {
        "Ocp-Apim-Subscription-Key": "Ctq9YrNAoLPj1QnunemGX6Gm0dWnAfn44NR5oSaM1skVuIWgfJyzJQQJ99BBACYeBjFXJ3w3AAAaACOGjIJU",
        "Content-Type": "application/json" 
    }

    payload = json.dumps({
        "top": 3,
        "question": question,
        "includeUnstructuredSources": True,
        "confidenceScoreThreshold": "0.5",
        "answerSpanRequest": {
            "enable": True,
            "topAnswersWithSpan": 1,
            "confidenceScoreThreshold": "0.5"
        }
    })

    try:
        response = requests.post(reqUrl, data=payload, headers=headersList)
        if response.status_code == 200:
            data = response.json()
            # Se asume que la respuesta tiene una clave "answers" con una lista de respuestas.
            answer = data.get("answers", [{}])[0].get("answer", "No se encontró respuesta.")
        else:
            answer = f"Error: {response.status_code} en la petición."
    except Exception as e:
        answer = f"Se produjo un error: {e}"

    # Simular streaming: ir rindiendo la respuesta carácter a carácter
    streamed_answer = ""
    for char in answer:
        streamed_answer += char
        yield streamed_answer  # Se rinde el texto acumulado hasta el momento.
        time.sleep(0.02)  # Pausa para simular efecto streaming

st.title("Pathfinder 2e QnA Chatbot")

# Inicializar historial de mensajes en session_state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar mensajes del historial en cada rerun de la app
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Aceptar input del usuario
if prompt := st.chat_input("Envía un mensaje..."):
    # Agregar mensaje del usuario al historial
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Mostrar mensaje del usuario
    with st.chat_message("user"):
        st.markdown(prompt)

    # Mostrar respuesta del asistente con efecto "streaming"
    with st.chat_message("assistant"):
        final_response = ""  # Aquí acumulamos la respuesta completa
        # Usamos un placeholder para actualizar el contenido a medida que llega cada trozo.
        placeholder = st.empty()
        for text in response_generator(prompt):
            placeholder.markdown(text)
            final_response = text  # Al final, 'final_response' contendrá la respuesta completa

    # Agregar respuesta del asistente al historial
    st.session_state.messages.append({"role": "assistant", "content": final_response})