"""
Construye el corpus de la base de conocimiento por TRIANGULACIÓN DE FUENTES.

Uso:
    python scripts/build_corpus.py

Genera 3 documentos en data/ (~21 páginas en total), uno por tipo de fuente:

    01_fuentes_primarias.txt  → los textos antiguos: Homero (Ilíada y Odisea, trad.
                                española de Luis Segalá, 1908-1910) y Hesíodo
                                (Teogonía, trad. inglesa de H. G. Evelyn-White, 1914)
    02_manual_clasico.txt     → Thomas Bulfinch, «The Age of Fable» (1855): el manual
                                de mitología de referencia del siglo XIX
    03_enciclopedia.txt       → Wikipedia en español: síntesis moderna

¿Por qué tres tipos de fuente?
------------------------------
Es el método de un historiador: la FUENTE PRIMARIA dice lo que contaban los
griegos (con sus versiones y contradicciones), el MANUAL lo narra de forma
ordenada y la ENCICLOPEDIA aporta contexto moderno. Con las tres, el agente
puede responder «según Hesíodo…» y contrastar versiones, que es justo lo que
pide el system prompt.

Todas las fuentes son de dominio público (Project Gutenberg) o de licencia
abierta (Wikipedia, CC BY-SA 4.0).

¿Por qué mezclar español e inglés?
----------------------------------
No existe traducción española de dominio público de la Teogonía ni un manual
de mitología en español de dominio público. Gemini Embeddings es multilingüe:
una pregunta en español recupera pasajes en inglés porque se compara el
SIGNIFICADO, no las palabras (lo verifica el notebook). Las respuestas son
siempre en español.

Preprocesado (Paso 2 del enunciado: limpieza y eliminación de ruido)
-------------------------------------------------------------------
- Gutenberg: se quitan la cabecera y la licencia del libro, se reconstruyen los
  párrafos (el texto viene cortado a 70 columnas), se eliminan los números de
  verso, las notas al pie y las ilustraciones, y se moderniza la ortografía de
  1908 («á», «ó», «é» átonas → «a», «o», «e»).
- Nombres latinos → griegos: Segalá y Bulfinch usan los nombres romanos
  (Júpiter, Minerva, Ulises). Se anota el nombre griego la primera vez que
  aparece en cada párrafo, «Minerva [Atenea]», sin alterar el original. Así una
  pregunta por «Atenea» recupera también los pasajes que dicen «Minerva».
- Wikipedia: texto plano sin secciones de ruido (Referencias, Enlaces…).
- Cada pasaje tiene un presupuesto de palabras, para equilibrar el corpus.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CACHE_DIR = PROJECT_ROOT / "scripts" / ".cache"

USER_AGENT = "MnemosineRAG/1.0 (proyecto educativo IA Generativa)"
WIKI_API_URL = "https://es.wikipedia.org/w/api.php"
WIKI_PAGE_URL = "https://es.wikipedia.org/wiki/"
GUTENBERG_TEXT_URL = "https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt"
GUTENBERG_PAGE_URL = "https://www.gutenberg.org/ebooks/{id}"

WORDS_PER_PAGE = 500
REQUEST_DELAY_SECONDS = 1.5
MAX_RETRIES = 6
RULE = "=" * 72


# ── Modelo de datos ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Section:
    """Una unidad citable del corpus (un pasaje o un artículo)."""
    title: str
    url: str
    source_type: str
    language: str
    text: str
    work: str = ""  # obra completa y traductor, cuando la sección es un pasaje

    def render(self) -> str:
        work_line = f"Obra: {self.work}\n" if self.work else ""
        return (
            f"{RULE}\nTítulo: {self.title}\nFuente: {self.url}\n"
            f"Tipo: {self.source_type}\nIdioma: {self.language}\n{work_line}{RULE}\n\n{self.text}"
        )


@dataclass(frozen=True)
class Passage:
    title: str          # se usa como cita: «Homero, Ilíada I»
    start_marker: str   # texto exacto donde empieza el pasaje
    max_words: int


@dataclass(frozen=True)
class GutenbergWork:
    ebook_id: int
    credit: str                       # autor, obra y traductor
    language: str
    passages: tuple[Passage, ...]
    name_glossary: dict[str, str] = field(default_factory=dict)
    noise_patterns: tuple[str, ...] = ()


# ── Glosarios de nombres latinos → griegos ───────────────────────────────────

LATIN_TO_GREEK_ES = {
    "Júpiter": "Zeus", "Juno": "Hera", "Minerva": "Atenea", "Neptuno": "Poseidón",
    "Venus": "Afrodita", "Vulcano": "Hefesto", "Marte": "Ares", "Mercurio": "Hermes",
    "Plutón": "Hades", "Ceres": "Deméter", "Diana": "Artemisa", "Baco": "Dioniso",
    "Saturno": "Crono", "Ulises": "Odiseo", "Hércules": "Heracles",
    "Proserpina": "Perséfone", "Latona": "Leto", "Aurora": "Eos",
}

LATIN_TO_GREEK_EN = {
    "Jupiter": "Zeus", "Jove": "Zeus", "Juno": "Hera", "Minerva": "Atenea",
    "Neptune": "Poseidón", "Venus": "Afrodita", "Vulcan": "Hefesto", "Mars": "Ares",
    "Mercury": "Hermes", "Pluto": "Hades", "Ceres": "Deméter", "Diana": "Artemisa",
    "Bacchus": "Dioniso", "Saturn": "Crono", "Ulysses": "Odiseo", "Hercules": "Heracles",
    "Proserpine": "Perséfone", "Latona": "Leto", "Cupid": "Eros", "Aurora": "Eos",
}


# ── Definición del corpus ────────────────────────────────────────────────────

ILIAD = GutenbergWork(
    ebook_id=57654,
    credit="Homero, Ilíada (trad. Luis Segalá y Estalella, 1908)",
    language="es",
    name_glossary=LATIN_TO_GREEK_ES,
    noise_patterns=(r"\[Ilustración[^\]]*\]",),
    passages=(
        Passage("Homero, Ilíada I — La cólera de Aquiles", "Canta, oh diosa, la cólera", 450),
        Passage("Homero, Ilíada XXII — La muerte de Héctor", "arremetió Héctor, blandiendo la aguda espada", 600),
    ),
)

ODYSSEY = GutenbergWork(
    ebook_id=58221,
    credit="Homero, Odisea (trad. Luis Segalá y Estalella, 1910)",
    language="es",
    name_glossary=LATIN_TO_GREEK_ES,
    noise_patterns=(r"\[Ilustración[^\]]*\]",),
    passages=(
        Passage("Homero, Odisea IX — El cíclope Polifemo", "De tal suerte habló, y volví", 550),
        Passage("Homero, Odisea XII — Las sirenas", "Llegarás primero á las Sirenas", 300),
    ),
)

THEOGONY = GutenbergWork(
    ebook_id=348,
    credit="Hesíodo, Teogonía (trad. inglesa de Hugh G. Evelyn-White, 1914)",
    language="en",
    noise_patterns=(r"\(ll\. ?\d+-\d+\)", r"(?<=\w)\s\d{3,4}\b"),  # referencias de verso y notas
    passages=(
        Passage("Hesíodo, Teogonía — El origen del mundo", "Verily at the first Chaos came to be", 250),
        Passage("Hesíodo, Teogonía — Crono devora a sus hijos", "But Rhea was subject in love to Cronos", 280),
        Passage("Hesíodo, Teogonía — Prometeo roba el fuego", "outwitted him and stole", 200),
        Passage("Hesíodo, Teogonía — La Titanomaquia", "Then Zeus no longer held back his might", 230),
    ),
)

AGE_OF_FABLE = GutenbergWork(
    ebook_id=4925,
    credit="Thomas Bulfinch, The Age of Fable (1855)",
    language="en",
    name_glossary=LATIN_TO_GREEK_EN,
    passages=(
        Passage("Bulfinch — Prometeo y Pandora", "Prometheus was one of the Titans", 350),
        Passage("Bulfinch — Perseo y Medusa", "Perseus was the son of Jupiter and Danae", 400),
        Passage("Bulfinch — Heracles", "Hercules was the son of Jupiter and Alcmena", 350),
        Passage("Bulfinch — Teseo y el Minotauro", "Theseus was the son of Aegeus", 400),
        Passage("Bulfinch — Jasón y el vellocino de oro", "In very ancient times there lived in Thessaly", 380),
        Passage("Bulfinch — Orfeo y Eurídice", "Orpheus was the son of Apollo and the Muse Calliope", 480),
        Passage("Bulfinch — La caída de Troya", "The story of the Iliad ends with the death of Hector", 330),
    ),
)

WIKIPEDIA_ARTICLES = (
    "Caos (mitología)", "Crono", "Titanomaquia", "Zeus", "Hera", "Poseidón", "Atenea",
    "Hades", "Perséfone", "Mnemósine", "Medusa (mitología)", "Minotauro", "Pegaso",
    "Guerra de Troya", "Caballo de Troya",
)
WIKIPEDIA_WORDS_PER_ARTICLE = 170

WIKI_NOISE_SECTIONS = {
    "referencias", "bibliografía", "enlaces externos", "véase también", "notas",
    "galería", "fuentes", "lecturas adicionales", "en la cultura popular",
    "cultura popular", "en la cultura moderna", "en la ficción", "filmografía",
    "notas y referencias", "citas", "bibliografía adicional", "influencia posterior",
}


@dataclass(frozen=True)
class CorpusDocument:
    filename: str
    title: str
    description: str
    build_sections: Callable[[], list["Section"]]


# ── Utilidades de red con caché ──────────────────────────────────────────────

def http_get(url: str, cache_file: Path) -> str:
    """GET con caché en disco y reintentos ante HTTP 429."""
    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                body = response.read().decode("utf-8")
            break
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt == MAX_RETRIES - 1:
                raise
            wait = int(error.headers.get("Retry-After") or 5 * 2**attempt)
            print(f"    HTTP 429, reintentando en {wait}s…")
            time.sleep(wait)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(body, encoding="utf-8")
    time.sleep(REQUEST_DELAY_SECONDS)
    return body


def truncate_words(paragraphs: list[str], max_words: int) -> list[str]:
    """Párrafos completos hasta superar max_words (nunca corta una frase a medias)."""
    kept, total = [], 0
    for paragraph in paragraphs:
        if total >= max_words:
            break
        kept.append(paragraph)
        total += len(paragraph.split())
    while kept and kept[-1].startswith("#"):
        kept.pop()
    return kept


# ── Project Gutenberg ────────────────────────────────────────────────────────

def gutenberg_paragraphs(ebook_id: int) -> list[str]:
    """Texto del libro sin la licencia de Gutenberg, con los párrafos reconstruidos."""
    raw = http_get(GUTENBERG_TEXT_URL.format(id=ebook_id), CACHE_DIR / "gutenberg" / f"{ebook_id}.txt")
    body = re.split(r"\*\*\* ?START OF.*?\*\*\*", raw, maxsplit=1)[-1]
    body = re.split(r"\*\*\* ?END OF", body, maxsplit=1)[0]
    blocks = re.split(r"\n\s*\n", body.replace("\r\n", "\n"))
    return [" ".join(block.split()) for block in blocks if block.strip()]


def modernize_spanish(text: str) -> str:
    """Ortografía de 1908 → actual: la preposición «á» y las conjunciones «ó», «é»."""
    return re.sub(r"\b([áóé])\b", lambda m: {"á": "a", "ó": "o", "é": "e"}[m[1]], text)


def annotate_names(paragraph: str, glossary: dict[str, str]) -> str:
    """Añade el nombre griego tras la primera aparición de cada nombre latino."""
    for latin, greek in glossary.items():
        paragraph = re.sub(rf"\b{latin}\b", f"{latin} [{greek}]", paragraph, count=1)
    return paragraph


def clean_passage(paragraph: str, work: GutenbergWork) -> str:
    for pattern in work.noise_patterns:
        paragraph = re.sub(pattern, "", paragraph)
    paragraph = re.sub(r"^\d+\s+", "", paragraph)  # número de verso al inicio
    paragraph = re.sub(r"_(\w[^_]*)_", r"\1", paragraph)  # cursivas de Gutenberg: _Nadie_
    if work.language == "es":
        paragraph = modernize_spanish(paragraph)
    if work.name_glossary:
        paragraph = annotate_names(paragraph, work.name_glossary)
    return " ".join(paragraph.split())


def extract_passage(paragraphs: list[str], passage: Passage) -> list[str]:
    """Desde el párrafo que contiene el marcador (completo, para no empezar a
    mitad de frase) hasta agotar el presupuesto de palabras."""
    for index, paragraph in enumerate(paragraphs):
        if passage.start_marker in paragraph:
            return truncate_words(paragraphs[index:], passage.max_words)
    raise ValueError(f"No se encontró el inicio del pasaje: {passage.title!r}")


def gutenberg_sections(work: GutenbergWork, source_type: str) -> list[Section]:
    paragraphs = gutenberg_paragraphs(work.ebook_id)
    sections = []
    for passage in work.passages:
        cleaned = [clean_passage(p, work) for p in extract_passage(paragraphs, passage)]
        cleaned = [p for p in cleaned if p]
        sections.append(Section(
            title=passage.title,
            url=GUTENBERG_PAGE_URL.format(id=work.ebook_id),
            source_type=source_type,
            language=work.language,
            text="\n\n".join(cleaned),
            work=work.credit,
        ))
    return sections


# ── Wikipedia ────────────────────────────────────────────────────────────────

def fetch_wikipedia_article(title: str) -> tuple[str, str]:
    params = {
        "action": "query", "prop": "extracts", "explaintext": 1, "redirects": 1,
        "titles": title, "format": "json", "formatversion": 2,
    }
    cache_file = CACHE_DIR / (re.sub(r"\W+", "_", title) + ".json")
    if cache_file.exists():
        page = json.loads(cache_file.read_text(encoding="utf-8"))
    else:
        body = http_get(f"{WIKI_API_URL}?{urllib.parse.urlencode(params)}", cache_file.with_suffix(".raw"))
        page = json.loads(body)["query"]["pages"][0]
        if "missing" in page:
            raise ValueError(f"Artículo no encontrado en Wikipedia: {title}")
        cache_file.write_text(json.dumps(page, ensure_ascii=False), encoding="utf-8")
    return page["title"], page["extract"]


def clean_wikipedia_text(text: str) -> list[str]:
    """Párrafos sin secciones de ruido; títulos «== X ==» → «## X»."""
    text = text.replace("​", "").replace("\xa0", " ")
    text = re.sub(r"\[\d+\]|\[cita requerida\]", "", text)
    lines: list[str] = []
    skipping, skip_level = False, 0
    for raw_line in text.splitlines():
        line = raw_line.strip()
        heading = re.match(r"^(=+)\s*(.*?)\s*=+$", line)
        if heading:
            level, name = len(heading.group(1)), heading.group(2)
            if skipping and level > skip_level:
                continue
            skipping, skip_level = name.lower() in WIKI_NOISE_SECTIONS, level
            if not skipping:
                lines.append(f"{'#' * level} {name}")
        elif line and not skipping:
            lines.append(line)
    return [
        line for i, line in enumerate(lines)
        if not (line.startswith("#") and (i + 1 == len(lines) or lines[i + 1].startswith("#")))
    ]


def wikipedia_sections() -> list[Section]:
    sections = []
    for article in WIKIPEDIA_ARTICLES:
        title, raw_text = fetch_wikipedia_article(article)
        body = truncate_words(clean_wikipedia_text(raw_text), WIKIPEDIA_WORDS_PER_ARTICLE)
        sections.append(Section(
            title=f"Wikipedia — {title}",
            url=WIKI_PAGE_URL + urllib.parse.quote(title.replace(" ", "_")),
            source_type="Enciclopedia",
            language="es",
            text="\n\n".join(body),
        ))
    return sections


# ── Documentos ───────────────────────────────────────────────────────────────

CORPUS: tuple[CorpusDocument, ...] = (
    CorpusDocument(
        filename="01_fuentes_primarias.txt",
        title="Fuentes primarias — Homero y Hesíodo",
        description="Pasajes de los poemas antiguos: lo que contaban los propios griegos.",
        build_sections=lambda: (
            gutenberg_sections(THEOGONY, "Fuente primaria")
            + gutenberg_sections(ILIAD, "Fuente primaria")
            + gutenberg_sections(ODYSSEY, "Fuente primaria")
        ),
    ),
    CorpusDocument(
        filename="02_manual_clasico.txt",
        title="Manual clásico — Thomas Bulfinch, The Age of Fable (1855)",
        description="Los mitos narrados de forma ordenada por el manual de referencia del siglo XIX.",
        build_sections=lambda: gutenberg_sections(AGE_OF_FABLE, "Manual clásico"),
    ),
    CorpusDocument(
        filename="03_enciclopedia.txt",
        title="Enciclopedia — Wikipedia en español",
        description="Síntesis moderna con contexto histórico y genealogías (CC BY-SA 4.0).",
        build_sections=wikipedia_sections,
    ),
)


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    for stale_file in DATA_DIR.glob("*.txt"):
        stale_file.unlink()

    grand_total = 0
    for document in CORPUS:
        sections = document.build_sections()
        header = f"# {document.title}\n\n{document.description}\n"
        content = "\n\n".join([header, *(section.render() for section in sections)]) + "\n"
        (DATA_DIR / document.filename).write_text(content, encoding="utf-8")

        words = sum(len(section.text.split()) for section in sections)
        grand_total += words
        print(f"\n{document.filename}: {len(sections)} secciones, {words} palabras (~{words / WORDS_PER_PAGE:.1f} págs.)")
        for section in sections:
            print(f"   {section.title}: {len(section.text.split())}")
    print(f"\nTOTAL: {grand_total} palabras (~{grand_total / WORDS_PER_PAGE:.0f} páginas)")


if __name__ == "__main__":
    main()
