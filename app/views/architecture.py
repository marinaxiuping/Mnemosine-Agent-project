"""Cómo funciona: la arquitectura RAG + LangGraph explicada."""

from __future__ import annotations

import streamlit as st

from app.ui import components
from src.config import DEFAULT_SETTINGS as SETTINGS

PIPELINE_DOT = """
digraph {
    graph [bgcolor="transparent", rankdir=LR, nodesep=0.4];
    node [shape=box, style="rounded,filled", fillcolor="#121726", color="#b99b5e", penwidth=1.4,
          fontcolor="#e8e0cc", fontname="Georgia", fontsize=13];
    edge [color="#b99b5e", penwidth=1.3];
    pregunta [shape=plaintext, style="", fontcolor="#9c937e"];
    respuesta [shape=plaintext, style="", fontcolor="#9c937e"];
    reformular [label="1 · Reformular\\n(con la memoria)"];
    recuperar [label="2 · Recuperar\\n(ChromaDB)"];
    generar [label="3 · Generar\\n(Gemini)"];
    memoria [label="Memoria\\n(thread_id)", shape=cylinder, color="#9c937e"];
    fuentes [label="Fuentes\\nprimaria · manual · enciclopedia", shape=cylinder, color="#9c937e"];
    pregunta -> reformular -> recuperar -> generar -> respuesta;
    memoria -> reformular [style=dashed, color="#9c937e"];
    memoria -> generar [style=dashed, color="#9c937e"];
    fuentes -> recuperar [style=dashed, color="#9c937e"];
}
"""


def render() -> None:
    components.hero("CÓMO FUNCIONA", "Recuperar, recordar y responder", compact=True)
    st.graphviz_chart(PIPELINE_DOT, width="stretch")

    with st.container(key="narrow-architecture"):
        st.markdown(
            f"""
Cada pregunta recorre un **grafo de LangGraph** con tres nodos:

1. **Reformular.** Si la pregunta depende de la conversación («¿y qué nació de su sangre?»), Gemini la
   reescribe como una consulta autónoma («¿qué nació de la sangre de Medusa?»). Sin este paso, la búsqueda
   no sabría de quién hablamos.
2. **Recuperar.** La consulta se convierte en un embedding (`{SETTINGS.embedding_model}`) y ChromaDB devuelve
   los **{SETTINGS.retrieval_k} fragmentos** más cercanos por similitud coseno, procedan de una fuente primaria,
   del manual o de la enciclopedia, y estén en español o en inglés.
3. **Generar.** `{SETTINGS.chat_model}` responde con el *system prompt*, los fragmentos y los últimos
   {SETTINGS.max_history_messages} mensajes, cita la fuente de cada dato y contrasta las versiones cuando difieren.

La **memoria** la guarda un *checkpointer* de LangGraph por conversación (`thread_id`). Cambiar de página no
la borra; solo «Nueva conversación» abre un hilo nuevo.
"""
        )
