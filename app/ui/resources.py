"""
Recursos compartidos por todas las páginas: agente, base de conocimiento y sesión.

- El agente y la base vectorial se crean UNA vez por servidor (st.cache_resource).
- Cada sesión de navegador tiene su propio thread_id: como la memoria de
  LangGraph va por hilo, dos usuarios nunca comparten conversación, y cambiar
  de página no borra el chat.
"""

from __future__ import annotations

import os
import uuid

import streamlit as st

from app.domain_content import CHARACTERS_BY_SLUG, PRESENTATION_PROMPT
from src.agent import RagAgent
from src.domain import ACTIVE_DOMAIN
from src.knowledge_base import KnowledgeBase


def ensure_api_key() -> None:
    """En Streamlit Cloud la key llega por st.secrets; en local, por .env."""
    if os.getenv("GOOGLE_API_KEY"):
        return
    try:
        os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]
    except (KeyError, FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        st.error("Falta GOOGLE_API_KEY: añádela a `.env` (local) o a los *Secrets* de Streamlit Cloud.")
        st.stop()


@st.cache_resource(show_spinner="Despertando a Mnemósine… (la primera vez se indexan las fuentes)")
def get_resources() -> tuple[RagAgent, KnowledgeBase]:
    knowledge_base = KnowledgeBase(ACTIVE_DOMAIN.collection_name)
    knowledge_base.load_or_build()
    return RagAgent(knowledge_base, ACTIVE_DOMAIN.system_prompt), knowledge_base


def init_session() -> None:
    st.session_state.setdefault("thread_id", str(uuid.uuid4()))
    st.session_state.setdefault("messages", [])  # [{role, content, reply?}]
    st.session_state.setdefault("show_sources", True)


def queue_question(question: str) -> None:
    """Callback de botones: deja la pregunta pendiente; el enrutador abre el oráculo."""
    st.session_state.pending_question = question


def queue_character(slug: str) -> None:
    """Callback del panteón: el enrutador abre la ficha de ese personaje."""
    st.session_state.pending_character = slug


@st.cache_data(show_spinner=False)
def character_presentation(slug: str) -> dict:
    """Presentación de un personaje generada con RAG. Se calcula una vez por
    servidor (st.cache_data) y en un hilo propio, para no tocar el chat del usuario."""
    agent, _ = get_resources()
    character = CHARACTERS_BY_SLUG[slug]
    reply = agent.ask(
        PRESENTATION_PROMPT.format(name=character.name),
        thread_id=f"presentation-{slug}-{uuid.uuid4()}",
    )
    return {"answer": reply.answer, "sources": [dict(source) for source in reply.sources]}


def start_new_conversation() -> None:
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.messages = []
