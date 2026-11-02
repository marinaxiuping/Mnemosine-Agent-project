"""
Base de conocimiento vectorial: carga de documentos → chunking → Gemini Embeddings → ChromaDB.

Es agnóstica al dominio: indexa cualquier .txt, .md o .pdf que haya en el
directorio de datos.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import DEFAULT_SETTINGS, Settings

TEXT_EXTENSIONS = {".txt", ".md"}
PDF_EXTENSIONS = {".pdf"}

# Un documento de texto puede contener varias fuentes, cada una precedida por una
# cabecera de metadatos «Clave: valor» entre dos reglas (formato que genera
# scripts/build_corpus.py):
#   ========
#   Título: Homero, Ilíada I — La cólera de Aquiles
#   Fuente: https://www.gutenberg.org/ebooks/57654
#   Tipo: Fuente primaria
#   Idioma: es
#   Obra: Homero, Ilíada (trad. Luis Segalá, 1908)   ← opcional
#   ========
# Si no hay cabeceras, el fichero entero se trata como una única fuente.
SOURCE_HEADER_PATTERN = re.compile(r"^={10,}\n(?P<fields>(?:[^\n=][^\n]*: [^\n]+\n)+)={10,}$", re.MULTILINE)
HEADER_FIELDS = {
    "Título": "title", "Fuente": "url", "Tipo": "source_type", "Idioma": "language", "Obra": "work",
}

# Se intenta cortar primero por secciones (##), luego por párrafos, frases y
# palabras: cada chunk respeta la estructura del texto todo lo posible.
# Son expresiones regulares con lookarounds (anchura cero): el corte de frase se
# hace DESPUÉS del punto, así ningún chunk empieza por «. » ni pierde su punto final.
SPLIT_SEPARATORS = [r"\n(?=#{2,3} )", r"\n\n", r"\n", r"(?<=[.!?»”]) ", r" ", r""]


@dataclass(frozen=True)
class SourceInfo:
    title: str
    url: str
    source_type: str
    language: str
    source_file: str
    chunk_count: int


@dataclass(frozen=True)
class SearchResult:
    document: Document
    score: float  # relevancia en [0, 1]: 1 - distancia coseno

    @property
    def title(self) -> str:
        return self.document.metadata.get("title", "Documento")

    @property
    def url(self) -> str:
        return self.document.metadata.get("url", "")

    @property
    def source_file(self) -> str:
        return self.document.metadata.get("source_file", "")

    @property
    def source_type(self) -> str:
        return self.document.metadata.get("source_type", "")


class KnowledgeBase:
    """Gestiona el ciclo de vida de la colección vectorial en ChromaDB."""

    def __init__(self, collection_name: str, settings: Settings = DEFAULT_SETTINGS):
        self.collection_name = collection_name
        self.settings = settings
        # La librería usa automáticamente task_type=RETRIEVAL_DOCUMENT al indexar
        # y RETRIEVAL_QUERY al buscar: Gemini optimiza cada embedding para su papel.
        self._embeddings = GoogleGenerativeAIEmbeddings(model=settings.embedding_model)
        self._vectorstore: Chroma | None = None

    # ── Construcción ─────────────────────────────────────────────────────────

    def load_documents(self) -> list[Document]:
        """Lee todos los ficheros soportados y los divide en fuentes con metadatos."""
        documents: list[Document] = []
        for path in sorted(self.settings.data_dir.rglob("*")):
            suffix = path.suffix.lower()
            if suffix in TEXT_EXTENSIONS:
                documents.extend(_parse_text_file(path))
            elif suffix in PDF_EXTENSIONS:
                documents.extend(_parse_pdf_file(path))
        if not documents:
            raise FileNotFoundError(f"No hay documentos indexables en {self.settings.data_dir}")
        return documents

    def split_documents(self, documents: list[Document]) -> list[Document]:
        """Divide en chunks y antepone a cada uno el título de su fuente.

        Ese prefijo («[Medusa] …») es un *contextual chunk header*: un fragmento
        como «fue decapitada por Perseo» no dice de quién habla; con el título
        delante, su embedding sí lo sabe y la búsqueda es más precisa.
        """
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
            separators=SPLIT_SEPARATORS,
            is_separator_regex=True,
        )
        chunks = splitter.split_documents(documents)
        for index, chunk in enumerate(chunks):
            chunk.page_content = f"[{chunk.metadata['title']}] {chunk.page_content.strip()}"
            chunk.metadata["chunk_id"] = index
        return chunks

    def build(self) -> Chroma:
        """(Re)construye la colección desde cero a partir de data/."""
        documents = self.load_documents()
        chunks = self.split_documents(documents)
        print(f"[KB] {len(documents)} fuentes → {len(chunks)} chunks")

        self._open_vectorstore().delete_collection()
        self._vectorstore = self._open_vectorstore()
        self._add_in_batches(chunks)
        print(f"[KB] Colección '{self.collection_name}' persistida en {self.settings.persist_dir}")
        return self._vectorstore

    def load_or_build(self, force_rebuild: bool = False) -> Chroma:
        """Carga la colección si ya existe en disco; si no, la construye."""
        vectorstore = self._open_vectorstore()
        if force_rebuild or self._count(vectorstore) == 0:
            return self.build()
        self._vectorstore = vectorstore
        print(f"[KB] Colección '{self.collection_name}' cargada ({self._count(vectorstore)} chunks)")
        return vectorstore

    # ── Consulta ─────────────────────────────────────────────────────────────

    def search(self, query: str, k: int | None = None) -> list[SearchResult]:
        """Devuelve los k chunks más relevantes con su puntuación de relevancia."""
        pairs = self.vectorstore.similarity_search_with_relevance_scores(
            query, k=k or self.settings.retrieval_k
        )
        return [SearchResult(document=doc, score=score) for doc, score in pairs]

    def describe(self) -> list[SourceInfo]:
        """Catálogo de fuentes indexadas, en el orden del corpus, con su nº de chunks."""
        metadatas = self.vectorstore.get(include=["metadatas"])["metadatas"]
        catalog: dict[str, SourceInfo] = {}
        for metadata in sorted(metadatas, key=lambda m: m["chunk_id"]):
            title = metadata["title"]
            previous = catalog.get(title)
            catalog[title] = SourceInfo(
                title=title,
                url=metadata["url"],
                source_type=metadata.get("source_type", ""),
                language=metadata.get("language", ""),
                source_file=metadata["source_file"],
                chunk_count=(previous.chunk_count if previous else 0) + 1,
            )
        return list(catalog.values())

    @property
    def vectorstore(self) -> Chroma:
        if self._vectorstore is None:
            raise RuntimeError("Llama primero a load_or_build() o build().")
        return self._vectorstore

    @property
    def chunk_count(self) -> int:
        return self._count(self.vectorstore)

    # ── Internos ─────────────────────────────────────────────────────────────

    def _open_vectorstore(self) -> Chroma:
        return Chroma(
            collection_name=self.collection_name,
            embedding_function=self._embeddings,
            persist_directory=str(self.settings.persist_dir),
            # Coseno: compara la DIRECCIÓN de los vectores (el significado), no su
            # magnitud. Es la métrica estándar para embeddings de texto.
            collection_configuration={"hnsw": {"space": "cosine"}},
        )

    def _add_in_batches(self, chunks: list[Document]) -> None:
        """Indexa respetando el límite de peticiones por minuto de la API."""
        size = self.settings.embedding_batch_size
        for start in range(0, len(chunks), size):
            batch = chunks[start:start + size]
            for attempt in range(1, self.settings.max_embedding_retries + 1):
                try:
                    self.vectorstore.add_documents(batch)
                    break
                except Exception as error:  # la librería no exporta su clase de error
                    if "RESOURCE_EXHAUSTED" not in str(error) or attempt == self.settings.max_embedding_retries:
                        raise
                    wait = self.settings.rate_limit_wait_seconds
                    print(f"[KB] Límite de la API alcanzado; reintento {attempt} en {wait}s…")
                    time.sleep(wait)
            print(f"[KB] Indexados {min(start + size, len(chunks))}/{len(chunks)} chunks")

    @staticmethod
    def _count(vectorstore: Chroma) -> int:
        return len(vectorstore.get(include=[])["ids"])


def _parse_text_file(path: Path) -> list[Document]:
    text = path.read_text(encoding="utf-8")
    headers = list(SOURCE_HEADER_PATTERN.finditer(text))
    if not headers:
        return [_make_document(text, path, {"title": path.stem})]

    documents = []
    for current, following in zip(headers, headers[1:] + [None]):
        end = following.start() if following else len(text)
        body = text[current.end():end].strip()
        if body:
            documents.append(_make_document(body, path, _parse_header(current["fields"])))
    return documents


def _parse_header(fields: str) -> dict[str, str]:
    metadata = {}
    for line in fields.strip().splitlines():
        key, _, value = line.partition(": ")
        if key in HEADER_FIELDS:
            metadata[HEADER_FIELDS[key]] = value.strip()
    return metadata


def _parse_pdf_file(path: Path) -> list[Document]:
    pages = PyPDFLoader(str(path)).load()
    return [
        _make_document(page.page_content, path, {"title": f"{path.stem} (p. {page.metadata.get('page', 0) + 1})"})
        for page in pages
        if page.page_content.strip()
    ]


def _make_document(text: str, path: Path, metadata: dict[str, str]) -> Document:
    """Todos los chunks llevan los mismos campos (Chroma no admite valores None)."""
    return Document(
        page_content=text,
        metadata={
            "source_file": path.name,
            "title": metadata.get("title", path.stem),
            "url": metadata.get("url", ""),
            "source_type": metadata.get("source_type", ""),
            "language": metadata.get("language", ""),
            "work": metadata.get("work", ""),
        },
    )
