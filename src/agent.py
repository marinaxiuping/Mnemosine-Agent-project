"""
Agente RAG con memoria construido con LangGraph.

Grafo:

    START → rewrite_query → retrieve → generate → END

- rewrite_query: convierte la pregunta en una consulta autónoma usando el
  historial («¿y qué nació de su sangre?» → «¿qué nació de la sangre de Medusa?»).
  Sin este paso, las preguntas de seguimiento recuperarían fragmentos irrelevantes.
- retrieve: busca en ChromaDB los k fragmentos más relevantes.
- generate: Gemini responde con system prompt + fragmentos + historial reciente.

Memoria: un checkpointer de LangGraph (MemorySaver) guarda el estado de cada
conversación bajo su `thread_id`. Cada usuario o sesión tiene su propio hilo,
así que las conversaciones no se mezclan.

El agente no conoce el dominio: recibe el system prompt y un buscador desde fuera.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Annotated, Protocol, TypedDict

from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    AnyMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from src.config import DEFAULT_SETTINGS, Settings
from src.knowledge_base import SearchResult
from src.prompts import (
    CONTEXT_TEMPLATE,
    FIRST_TURN_NOTE,
    QUERY_REWRITE_PROMPT,
    TRIMMED_HISTORY_NOTE,
)

REWRITE_NODE = "rewrite_query"
RETRIEVE_NODE = "retrieve"
GENERATE_NODE = "generate"


class Searcher(Protocol):
    """Cualquier objeto con este método sirve como fuente de contexto."""

    def search(self, query: str, k: int | None = None) -> list[SearchResult]: ...


class Source(TypedDict):
    title: str
    url: str
    source_file: str
    source_type: str
    score: float
    excerpt: str


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    search_query: str
    context: str
    sources: list[Source]


@dataclass
class AgentReply:
    answer: str
    search_query: str
    sources: list[Source] = field(default_factory=list)


class RagAgent:
    """Agente experto: RAG sobre una base vectorial + LLM Gemini + memoria por hilo."""

    def __init__(
        self,
        searcher: Searcher,
        system_prompt: str,
        settings: Settings = DEFAULT_SETTINGS,
        checkpointer: BaseCheckpointSaver | None = None,
    ):
        self._searcher = searcher
        self._system_prompt = system_prompt
        self._settings = settings
        self._answer_llm = ChatGoogleGenerativeAI(
            model=settings.chat_model, temperature=settings.answer_temperature
        )
        self._rewrite_llm = ChatGoogleGenerativeAI(
            model=settings.chat_model, temperature=settings.rewrite_temperature
        )
        self.graph = self._build_graph(checkpointer or MemorySaver())

    # ── API pública ──────────────────────────────────────────────────────────

    def ask(self, question: str, thread_id: str) -> AgentReply:
        """Responde una pregunta dentro de la conversación `thread_id`."""
        state = self.graph.invoke(
            {"messages": [HumanMessage(content=question)]}, self._config(thread_id)
        )
        return self._reply_from_state(state)

    def stream(self, question: str, thread_id: str) -> Iterator[str]:
        """Igual que ask(), pero va devolviendo la respuesta token a token.

        Pasa por el MISMO grafo (y por tanto por la misma memoria) que ask().
        Al terminar, last_reply(thread_id) devuelve fuentes y consulta usada.
        """
        for chunk, metadata in self.graph.stream(
            {"messages": [HumanMessage(content=question)]},
            self._config(thread_id),
            stream_mode="messages",
        ):
            # Solo los tokens del nodo de respuesta (no los de la reformulación).
            if metadata.get("langgraph_node") == GENERATE_NODE and isinstance(chunk, AIMessageChunk):
                text = message_text(chunk)
                if text:
                    yield text

    def last_reply(self, thread_id: str) -> AgentReply | None:
        state = self.graph.get_state(self._config(thread_id)).values
        return self._reply_from_state(state) if state.get("messages") else None

    def history(self, thread_id: str) -> list[dict[str, str]]:
        """Historial completo de la conversación como [{role, content}]."""
        state = self.graph.get_state(self._config(thread_id)).values
        roles = {HumanMessage: "user", AIMessage: "assistant"}
        return [
            {"role": roles[type(message)], "content": message_text(message)}
            for message in state.get("messages", [])
            if type(message) in roles
        ]

    # ── Nodos del grafo ──────────────────────────────────────────────────────

    def _rewrite_query(self, state: AgentState) -> dict:
        question = message_text(state["messages"][-1])
        previous = state["messages"][:-1]
        if not previous:
            return {"search_query": question}  # primer turno: nada que resolver

        recent = previous[-self._settings.max_history_messages:]
        history = "\n".join(
            f"{'Usuario' if isinstance(m, HumanMessage) else 'Asistente'}: {message_text(m)}"
            for m in recent
        )
        prompt = QUERY_REWRITE_PROMPT.format(history=history, question=question)
        rewritten = message_text(self._rewrite_llm.invoke(prompt)).strip()
        return {"search_query": rewritten or question}

    def _retrieve(self, state: AgentState) -> dict:
        results = self._searcher.search(state["search_query"], k=self._settings.retrieval_k)
        context = "\n\n---\n\n".join(
            f"(Tipo de fuente: {result.source_type or 'sin especificar'})\n{result.document.page_content}"
            for result in results
        )
        sources = [
            Source(
                title=result.title,
                url=result.url,
                source_file=result.source_file,
                source_type=result.source_type,
                score=round(result.score, 3),
                excerpt=result.document.page_content,
            )
            for result in results
        ]
        return {"context": context, "sources": sources}

    def _generate(self, state: AgentState) -> dict:
        window = self._recent_messages(state["messages"])
        system = SystemMessage(
            content=self._system_prompt
            + self._conversation_note(len(window), len(state["messages"]))
            + CONTEXT_TEMPLATE.format(context=state["context"])
        )
        response = self._answer_llm.invoke([system, *window])
        return {"messages": [AIMessage(content=message_text(response), id=response.id)]}

    # ── Internos ─────────────────────────────────────────────────────────────

    def _build_graph(self, checkpointer: BaseCheckpointSaver):
        builder = StateGraph(AgentState)
        builder.add_node(REWRITE_NODE, self._rewrite_query)
        builder.add_node(RETRIEVE_NODE, self._retrieve)
        builder.add_node(GENERATE_NODE, self._generate)
        builder.add_edge(START, REWRITE_NODE)
        builder.add_edge(REWRITE_NODE, RETRIEVE_NODE)
        builder.add_edge(RETRIEVE_NODE, GENERATE_NODE)
        builder.add_edge(GENERATE_NODE, END)
        return builder.compile(checkpointer=checkpointer)

    def _recent_messages(self, messages: list[AnyMessage]) -> list[AnyMessage]:
        """Ventana de los últimos N mensajes, empezando siempre por una pregunta."""
        window = messages[-self._settings.max_history_messages:]
        while window and not isinstance(window[0], HumanMessage):
            window = window[1:]
        return window

    @staticmethod
    def _conversation_note(visible: int, total: int) -> str:
        """Le dice al LLM qué parte de la conversación está viendo."""
        if total == 1:
            return FIRST_TURN_NOTE
        if visible < total:
            return TRIMMED_HISTORY_NOTE.format(visible=visible, total=total)
        return ""

    @staticmethod
    def _config(thread_id: str) -> dict:
        return {"configurable": {"thread_id": thread_id}}

    @staticmethod
    def _reply_from_state(state: dict) -> AgentReply:
        return AgentReply(
            answer=message_text(state["messages"][-1]),
            search_query=state.get("search_query", ""),
            sources=state.get("sources", []),
        )


def message_text(message: AnyMessage) -> str:
    """Texto de un mensaje. Los modelos Gemini recientes pueden devolver el
    contenido como lista de bloques (texto, firmas de razonamiento…)."""
    content = message.content
    if isinstance(content, str):
        return content
    return "".join(
        block.get("text", "") if isinstance(block, dict) else str(block)
        for block in content
    )
