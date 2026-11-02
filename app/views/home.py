"""Inicio: presentación, panteón (abre la ficha de cada personaje), fuentes y chat libre."""

from __future__ import annotations

import html

import streamlit as st

from app.domain_content import SOURCE_KINDS
from app.ui import components
from app.ui.resources import queue_character, queue_question
from src.domain import ACTIVE_DOMAIN


def render(oracle_page) -> None:
    # Chat libre fijo abajo, para quien no quiera empezar por ningún personaje.
    free_question = st.chat_input("O pregunta lo que quieras a Mnemósine…")
    if free_question:
        queue_question(free_question)
        st.switch_page(oracle_page)

    components.hero(ACTIVE_DOMAIN.assistant_name.upper(), "Titánide de la memoria · guardiana de los mitos griegos")

    with st.container(key="narrow-home"):
        st.markdown(
            f'<p class="intro">{html.escape(ACTIVE_DOMAIN.welcome_message)}</p>',
            unsafe_allow_html=True,
        )
        if st.session_state.messages:
            st.page_link(oracle_page, label="Continuar la conversación", icon=":material/forum:")

        components.section_title("CONOCE A LOS PERSONAJES")
        components.pantheon_grid(on_select=queue_character)

        components.section_title("LAS TRES FUENTES DE LA MEMORIA")
        cards = "".join(
            f'<div class="kind-card"><div class="kind-numeral">{kind.numeral}</div>'
            f"<div class=\"kind-name\">{html.escape(kind.name)}</div>"
            f"<div class=\"kind-summary\">{html.escape(kind.summary)}</div>"
            f"<div class=\"kind-works\">{html.escape(kind.works)}</div></div>"
            for kind in SOURCE_KINDS
        )
        st.markdown(f'<div class="kind-grid">{cards}</div>', unsafe_allow_html=True)
