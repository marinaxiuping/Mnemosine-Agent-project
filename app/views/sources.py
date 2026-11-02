"""Fuentes: catálogo de la base de conocimiento, agrupado por tipo de fuente."""

from __future__ import annotations

import html

import streamlit as st

from app.domain_content import SOURCE_KINDS
from app.ui import components
from app.ui.resources import get_resources

LANGUAGE_LABELS = {"es": "ES", "en": "EN"}


def render() -> None:
    _, knowledge_base = get_resources()
    catalog = knowledge_base.describe()
    components.hero("FUENTES", "De dónde salen los recuerdos de Mnemósine", compact=True)

    with st.container(key="narrow-sources"):
        st.markdown(
            '<p class="intro">La base de conocimiento <b>triangula tres tipos de fuente</b>, como haría un '
            "historiador. Las fuentes primarias recogen lo que contaban los propios griegos, con sus "
            "versiones y contradicciones; el manual las narra con orden, y la enciclopedia aporta contexto "
            "moderno. Los textos en inglés se buscan igual que los españoles, porque los embeddings de "
            "Gemini comparan significados y no palabras.</p>",
            unsafe_allow_html=True,
        )
        for kind in SOURCE_KINDS:
            entries = [entry for entry in catalog if entry.source_type == kind.name]
            if not entries:
                continue
            chunks = sum(entry.chunk_count for entry in entries)
            components.section_title(f"{kind.numeral} · {kind.name.upper()}")
            st.caption(f"{kind.summary} {len(entries)} fuentes · {chunks} fragmentos indexados")
            rows = "".join(
                f'<li><a href="{html.escape(entry.url)}" target="_blank">{html.escape(entry.title)}</a>'
                f'<span class="badge">{LANGUAGE_LABELS.get(entry.language, entry.language.upper())}</span>'
                f'<span class="chunks">{entry.chunk_count} frag.</span></li>'
                for entry in entries
            )
            st.markdown(f'<ul class="source-list">{rows}</ul>', unsafe_allow_html=True)

        st.caption(
            "Homero, Hesíodo y Bulfinch: dominio público (Project Gutenberg). "
            "Wikipedia: CC BY-SA 4.0. Los nombres latinos de las traducciones antiguas se anotan "
            "con su equivalente griego: «Minerva [Atenea]»."
        )
