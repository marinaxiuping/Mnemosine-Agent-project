"""
Interfaz web de Mnemósine (punto de entrada).

Ejecutar desde la raíz del proyecto:
    streamlit run app/streamlit_app.py

Estructura:
- app/ui/resources.py   → agente, base vectorial y sesión (compartidos)
- app/ui/components.py  → piezas visuales reutilizables
- app/views/*.py        → una función render() por página (character.py: ficha de personaje)
- app/domain_content.py → panteón, genealogías y tipos de fuente (lo específico del tema)

Este archivo solo configura la página, la navegación y la barra lateral.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR.parent))  # permite importar app/ y src/ con `streamlit run`

from app.ui import components  # noqa: E402
from app.ui.resources import ensure_api_key, get_resources, init_session, start_new_conversation  # noqa: E402
from app.views import architecture, character, genealogy, home, oracle, sources  # noqa: E402
from src.domain import ACTIVE_DOMAIN  # noqa: E402


def render_sidebar() -> None:
    _, knowledge_base = get_resources()
    with st.sidebar:
        st.image(components.ASSISTANT_AVATAR, width=56)
        st.markdown(f"### {ACTIVE_DOMAIN.assistant_name}")

        questions = sum(1 for m in st.session_state.messages if m["role"] == "user")
        st.markdown(
            f'<div class="sidebar-meta">Experta en {ACTIVE_DOMAIN.domain_name.lower()}.</div>',
            unsafe_allow_html=True,
        )
        stats = (
            (questions, "pregunta" if questions == 1 else "preguntas"),
            (len(knowledge_base.describe()), "fuentes"),
            (knowledge_base.chunk_count, "fragmentos"),
        )
        cards = "".join(f'<div class="stat"><b>{value}</b><small>{label}</small></div>' for value, label in stats)
        st.markdown(f'<div class="stat-grid">{cards}</div>', unsafe_allow_html=True)

        st.divider()
        st.toggle("Mostrar búsqueda y fuentes", key="show_sources")
        st.button("Nueva conversación", icon=":material/restart_alt:",
                  on_click=start_new_conversation, width="stretch")


def main() -> None:
    st.set_page_config(
        page_title=f"{ACTIVE_DOMAIN.assistant_name} · {ACTIVE_DOMAIN.domain_name}",
        page_icon=components.ASSISTANT_AVATAR,
        layout="wide",
    )
    components.load_theme(APP_DIR / "theme.css")
    ensure_api_key()
    init_session()

    oracle_page = st.Page(oracle.render, title="Oráculo", icon=":material/forum:", url_path="oraculo")
    home_page = st.Page(lambda: home.render(oracle_page), title="Inicio", icon=":material/account_balance:",
                        url_path="inicio", default=True)
    character_page = st.Page(lambda: character.render(home_page, oracle_page), title="Personaje",
                             icon=":material/person:", url_path="personaje", visibility="hidden")
    pages = [
        home_page,
        oracle_page,
        st.Page(genealogy.render, title="Genealogía", icon=":material/account_tree:", url_path="genealogia"),
        st.Page(sources.render, title="Fuentes", icon=":material/menu_book:", url_path="fuentes"),
        st.Page(architecture.render, title="Cómo funciona", icon=":material/schema:", url_path="como-funciona"),
        character_page,  # oculta en el menú: se llega desde el panteón
    ]
    current_page = st.navigation(pages, position="top")

    # Enrutado centralizado (los callbacks de los botones no pueden cambiar de página):
    # - un personaje elegido en el panteón abre su ficha;
    # - una pregunta lanzada desde cualquier página abre el oráculo.
    if slug := st.session_state.pop("pending_character", None):
        st.switch_page(character_page, query_params={character.QUERY_PARAM: slug})
    if st.session_state.get("pending_question") and current_page.url_path != oracle_page.url_path:
        st.switch_page(oracle_page)

    current_page.run()
    render_sidebar()  # después de la página, para que el contador de preguntas esté al día


main()
