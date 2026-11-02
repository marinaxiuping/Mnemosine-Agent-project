"""
Configuración técnica del sistema RAG.

Todo lo que es un "número mágico" vive aquí, con su justificación, en vez de
estar repartido por el código. Lo específico del dominio (nombre del asistente,
prompts, colección…) NO está aquí, sino en `src/domain.py`: así el motor sirve
para cualquier tema sin tocar este archivo.

Los modelos se pueden cambiar sin tocar código mediante variables de entorno
(`GEMINI_CHAT_MODEL`, `GEMINI_EMBEDDING_MODEL`).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    # ── Rutas ───────────────────────────────────────────────────────────────
    # Absolutas respecto a la raíz del proyecto: funcionan igual desde el
    # notebook (notebooks/), desde Streamlit (app/) o desde la terminal.
    data_dir: Path = PROJECT_ROOT / "data"
    persist_dir: Path = PROJECT_ROOT / "chroma_db"

    # ── Modelos ─────────────────────────────────────────────────────────────
    # gemini-3.5-flash-lite: el modelo de la familia Flash más rápido y barato.
    # Para RAG la "inteligencia" la aporta sobre todo el contexto recuperado, así
    # que priorizamos latencia baja (importante en una demo en vivo) y coste.
    chat_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_CHAT_MODEL", "gemini-3.5-flash-lite")
    )
    # gemini-embedding-2: modelo de embeddings actual de Google, multilingüe
    # (nuestro corpus está en español) y de 3072 dimensiones.
    embedding_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-2")
    )

    # 0.3: respuestas fieles a las fuentes (temperatura baja) pero con una
    # redacción natural y algo de estilo narrativo (no 0).
    answer_temperature: float = 0.3
    # 0.0: reformular la pregunta es una tarea determinista; no queremos creatividad.
    rewrite_temperature: float = 0.0

    # ── Chunking ────────────────────────────────────────────────────────────
    # ~1000 caracteres ≈ 150-180 palabras ≈ 1-2 párrafos de Wikipedia: suficiente
    # para contener un episodio mítico completo (quién, qué, por qué). Chunks más
    # grandes mezclan episodios y "diluyen" el embedding; más pequeños pierden
    # el sujeto de la acción.
    chunk_size: int = 1000
    # 15 % de solapamiento: una frase cortada entre dos chunks aparece entera en
    # al menos uno de ellos.
    chunk_overlap: int = 150

    # ── Indexación ──────────────────────────────────────────────────────────
    # La capa gratuita de Gemini permite 100 embeddings por minuto. Indexamos en
    # lotes por debajo de ese límite y, si aun así la API responde 429, esperamos
    # un minuto y reintentamos el lote, en vez de abortar la construcción.
    embedding_batch_size: int = 80
    rate_limit_wait_seconds: int = 60
    max_embedding_retries: int = 5

    # ── Recuperación ────────────────────────────────────────────────────────
    # k = 4 chunks ≈ 4000 caracteres ≈ 1000 tokens de contexto: cubre preguntas
    # que cruzan dos personajes (p. ej. Perseo y Medusa) sin meter ruido que
    # distraiga al modelo.
    retrieval_k: int = 4

    # ── Memoria ─────────────────────────────────────────────────────────────
    # El historial COMPLETO se guarda en el checkpointer de LangGraph, pero al
    # LLM solo se le envían los últimos N mensajes (5 turnos pregunta-respuesta).
    # Así la conversación puede ser infinita sin desbordar el contexto ni
    # disparar el coste por llamada.
    max_history_messages: int = 10


DEFAULT_SETTINGS = Settings()
