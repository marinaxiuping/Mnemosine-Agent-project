"""Oráculo: el chat con Mnemósine."""

from __future__ import annotations

import streamlit as st

from app.ui import components
from app.ui.resources import get_resources, queue_question
from src.agent import RagAgent
from src.domain import ACTIVE_DOMAIN


def render() -> None:
    agent, _ = get_resources()
    components.hero(ACTIVE_DOMAIN.assistant_name.upper(), "Pregunta y recordaré", compact=True)

    typed_question = st.chat_input("Pregunta a Mnemósine por un dios, un héroe o un mito…")
    question = typed_question or st.session_state.pop("pending_question", None)

    with st.container(key="narrow-chat"):
        if not st.session_state.messages and not question:
            _welcome()
        _history()
        if question:
            _answer(agent, question)


def _welcome() -> None:
    with st.chat_message("assistant", avatar=components.ASSISTANT_AVATAR):
        st.markdown(ACTIVE_DOMAIN.welcome_message)
    components.section_title("PARA EMPEZAR")
    with st.container(key="examples"):
        for index, question in enumerate(ACTIVE_DOMAIN.example_questions):
            st.button(question, on_click=queue_question, args=(question,), key=f"example-{index}")


def _history() -> None:
    previous_question = ""
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar=components.avatar_for(message["role"])):
            st.markdown(message["content"])
            if message["role"] == "assistant" and message.get("reply"):
                components.reply_details(previous_question, message["reply"])
        if message["role"] == "user":
            previous_question = message["content"]


def _answer(agent: RagAgent, question: str) -> None:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user", avatar=components.USER_AVATAR):
        st.markdown(question)

    thread_id = st.session_state.thread_id
    with st.chat_message("assistant", avatar=components.ASSISTANT_AVATAR):
        with st.spinner("Mnemósine consulta sus recuerdos…"):
            tokens = agent.stream(question, thread_id)
            first_token = next(tokens, "")  # el spinner se mantiene hasta el primer token
        text = st.write_stream(_prepend(first_token, tokens))
        reply = agent.last_reply(thread_id)
        if reply:
            components.reply_details(question, reply)

    st.session_state.messages.append({"role": "assistant", "content": text, "reply": reply})


def _prepend(first: str, rest):
    yield first
    yield from rest
