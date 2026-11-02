"""Genealogía: tres árboles pequeños en pestañas, a todo el ancho de la página."""

from __future__ import annotations

import streamlit as st

from app.domain_content import FAMILY_TREES, GENEALOGY_LEGEND_HTML
from app.ui import components


def render() -> None:
    components.hero("GENEALOGÍA", "Quién desciende de quién, del Caos a los héroes", compact=True)
    st.markdown(f'<div class="legend">{GENEALOGY_LEGEND_HTML}</div>', unsafe_allow_html=True)

    for tab, tree in zip(st.tabs([tree.title for tree in FAMILY_TREES]), FAMILY_TREES):
        with tab:
            st.caption(tree.description)
            st.graphviz_chart(tree.dot, width="stretch" if tree.stretch else "content")
