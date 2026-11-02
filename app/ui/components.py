"""Componentes visuales reutilizables (cabecera, tarjetas, medallones, avatares)."""

from __future__ import annotations

import base64
import html
import re
from pathlib import Path

import streamlit as st

from app.domain_content import PANTHEON, Character
from src.agent import AgentReply, Source

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
ASSISTANT_AVATAR = str(ASSETS_DIR / "mnemosine.svg")
USER_AVATAR = str(ASSETS_DIR / "visitor.svg")
EXCERPT_LENGTH = 280  # caracteres de texto visibles por fragmento


def avatar_for(role: str) -> str:
    return USER_AVATAR if role == "user" else ASSISTANT_AVATAR


def load_theme(css_path: Path) -> None:
    """Inyecta la hoja de estilos, el contenido del panteón y el cielo del zodiaco.

    Streamlit no sirve ficheros estáticos sin configuración extra, así que el SVG de
    las constelaciones se incrusta como data URI en la variable CSS --zodiac.
    """
    zodiac = base64.b64encode((ASSETS_DIR / "zodiac.svg").read_bytes()).decode("ascii")
    zodiac_rule = f':root {{ --zodiac: url("data:image/svg+xml;base64,{zodiac}"); }}'
    css = css_path.read_text(encoding="utf-8") + zodiac_rule + pantheon_css()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def hero(title: str, subtitle: str, compact: bool = False) -> None:
    size_class = "hero compact" if compact else "hero"
    st.markdown(
        f"""
        <div class="{size_class}">
            <div class="hero-greek">ΜΝΗΜΟΣΥΝΗ</div>
            <div class="hero-title">{html.escape(title)}</div>
            <div class="hero-subtitle">{html.escape(subtitle)}</div>
        </div>
        <div class="meander"></div>
        """,
        unsafe_allow_html=True,
    )


def section_title(text: str) -> None:
    st.markdown(f'<div class="section-title">{html.escape(text)}</div>', unsafe_allow_html=True)


# ── Panteón: botones con medallón ────────────────────────────────────────────

def pantheon_button_key(character: Character) -> str:
    return f"god-{character.slug}"


def pantheon_css() -> str:
    """Cada botón del panteón muestra su monograma y su nombre griego con CSS
    (::before / ::after), así toda la tarjeta es clicable."""
    rules = [
        f'.st-key-{pantheon_button_key(c)} button::before {{ content: "{c.monogram}"; }}\n'
        f'.st-key-{pantheon_button_key(c)} button::after {{ content: "{c.greek_name}"; }}'
        for c in PANTHEON
    ]
    return "\n".join(rules)


def pantheon_grid(on_select, columns: int = 4) -> None:
    """Rejilla de personajes; on_select recibe el slug del elegido."""
    with st.container(key="pantheon"):
        grid = st.columns(columns)
        for index, character in enumerate(PANTHEON):
            grid[index % columns].button(
                character.name,
                help=f"{character.epithet} · ver su ficha",
                on_click=on_select,
                args=(character.slug,),
                key=pantheon_button_key(character),
                width="stretch",
            )


def source_chips(sources: list[Source]) -> None:
    """Fuentes compactas: un chip por título (varios chunks del mismo pasaje cuentan una vez)."""
    titles = list(dict.fromkeys(source["title"] for source in sources))
    chips = "".join(f'<span class="chip">{html.escape(title)}</span>' for title in titles)
    st.markdown(f'<div class="chips">Fuentes: {chips}</div>', unsafe_allow_html=True)


# ── Fuentes bajo cada respuesta ──────────────────────────────────────────────

def format_excerpt(raw_text: str) -> str:
    """Fragmento legible en HTML: sin la cabecera «[Título]», títulos de sección en
    negrita y todo en una sola línea (un salto de línea rompería el bloque HTML)."""
    body = raw_text.split("] ", 1)[-1]
    parts: list[str] = []
    remaining = EXCERPT_LENGTH  # se cuenta sobre texto plano, antes de escapar
    for line in filter(None, (line.strip() for line in body.splitlines())):
        heading = re.match(r"^#+\s*(.+)$", line)
        plain = heading[1] if heading else line
        if len(plain) > remaining:
            parts.append(html.escape(plain[:remaining].rsplit(" ", 1)[0]) + "…")
            break
        parts.append(f"<b>{html.escape(plain)}</b> ·" if heading else html.escape(plain))
        remaining -= len(plain)
    return " ".join(parts)


def source_card(source: Source) -> str:
    relevance = max(0, min(100, round(source["score"] * 100)))
    title = html.escape(source["title"])
    title_html = (
        f'<a class="source-title" href="{html.escape(source["url"])}" target="_blank">{title}</a>'
        if source["url"] else f'<span class="source-title">{title}</span>'
    )
    kind = html.escape(source.get("source_type") or "Fuente")
    return (
        f'<div class="source-card">'
        f'<div class="source-head">{title_html}'
        f'<span class="source-meta"><span class="badge">{kind}</span> relevancia {relevance}%</span></div>'
        f'<div class="relevance"><span style="width:{relevance}%"></span></div>'
        f'<div class="source-excerpt">{format_excerpt(source["excerpt"])}</div>'
        f"</div>"
    )


def reply_details(question: str, reply: AgentReply) -> None:
    """Consulta reformulada + fuentes consultadas, debajo de cada respuesta."""
    if not st.session_state.get("show_sources", True):
        return
    if reply.search_query and reply.search_query.strip() != question.strip():
        st.markdown(
            f'<div class="search-query">Búsqueda reformulada con la memoria: '
            f"<b>{html.escape(reply.search_query)}</b></div>",
            unsafe_allow_html=True,
        )
    if reply.sources:
        with st.expander(f"{len(reply.sources)} fragmentos consultados", icon=":material/menu_book:"):
            for source in reply.sources:
                st.markdown(source_card(source), unsafe_allow_html=True)
