"""Ficha de personaje: presentación, datos y preguntas sobre sus mitos.

Se abre desde el panteón de Inicio con la URL ?personaje=<slug>, así que cada
ficha se puede compartir o recargar.
"""

from __future__ import annotations

import html

import streamlit as st

from app.domain_content import CHARACTERS_BY_SLUG, FREE_QUESTION_TEMPLATE, Character
from app.ui import components
from app.ui.resources import character_presentation, queue_question

QUERY_PARAM = "personaje"


def render(home_page, oracle_page) -> None:
    character = CHARACTERS_BY_SLUG.get(st.query_params.get(QUERY_PARAM, ""))
    if character is None:
        st.warning("No encuentro a ese personaje en mi memoria.")
        st.page_link(home_page, label="Volver al panteón", icon=":material/arrow_back:")
        return

    # Chat libre fijo abajo: la pregunta lleva el personaje delante para dar contexto.
    free_question = st.chat_input(f"Pregunta lo que quieras sobre {character.name}…")
    if free_question:
        queue_question(FREE_QUESTION_TEMPLATE.format(name=character.name, question=free_question))
        st.switch_page(oracle_page)

    with st.container(key="narrow-character"):
        st.page_link(home_page, label="Volver al panteón", icon=":material/arrow_back:")
        _header(character)

        facts_column, story_column = st.columns([2, 3], gap="large")
        with facts_column:
            _facts(character)
        with story_column:
            _presentation(character)

        components.section_title(f"PREGÚNTALE A MNEMÓSINE POR {character.name.upper()}")
        with st.container(key="character-questions"):
            grid = st.columns(2)
            for index, question in enumerate(character.questions):
                grid[index % 2].button(
                    question, on_click=queue_question, args=(question,),
                    key=f"question-{character.slug}-{index}", width="stretch",
                )


def _header(character: Character) -> None:
    st.markdown(
        f"""
        <div class="profile-header">
            <div class="medallion-lg">{html.escape(character.monogram)}</div>
            <div class="profile-kind">{html.escape(character.kind.upper())}</div>
            <div class="profile-name">{html.escape(character.name)}</div>
            <div class="profile-greek">{html.escape(character.greek_name)}</div>
            <div class="profile-epithet">{html.escape(character.epithet)}</div>
        </div>
        <div class="meander"></div>
        """,
        unsafe_allow_html=True,
    )


def _facts(character: Character) -> None:
    rows = (("Padres", character.parents), ("Dominios", character.domains), ("Símbolos", character.symbols))
    items = "".join(f"<dt>{label}</dt><dd>{html.escape(value)}</dd>" for label, value in rows)
    st.markdown(f'<dl class="fact-card">{items}</dl>', unsafe_allow_html=True)


def _presentation(character: Character) -> None:
    st.markdown('<div class="story-label">LO QUE RECUERDA MNEMÓSINE</div>', unsafe_allow_html=True)
    with st.spinner(f"Mnemósine recuerda a {character.name}…"):
        presentation = character_presentation(character.slug)
    st.markdown(presentation["answer"])
    if presentation["sources"]:
        components.source_chips(presentation["sources"])
