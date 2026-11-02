"""
Contenido visual específico del dominio: panteón, árboles genealógicos y tipos de fuente.

Separado de las vistas para que la lógica de la interfaz no dependa del tema.
"""

from __future__ import annotations

from dataclasses import dataclass


# ── Panteón ──────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Character:
    """Ficha de un personaje.

    Los datos de la ficha (padres, dominios, símbolos) son fijos y verificables;
    la presentación narrativa la genera el agente con RAG. Las preguntas están
    elegidas para que la base de conocimiento pueda responderlas.
    """
    slug: str                 # identificador ASCII (URL, clave del botón y clase CSS)
    name: str
    greek_name: str
    monogram: str             # iniciales griegas del medallón
    epithet: str
    kind: str                 # Dios olímpico, Titán, Héroe…
    parents: str
    domains: str
    symbols: str
    questions: tuple[str, ...]


PANTHEON: tuple[Character, ...] = (
    Character(
        "zeus", "Zeus", "Ζεύς", "ΖΕ", "Rey del Olimpo", "Dios olímpico",
        parents="Crono y Rea", domains="El cielo, el trueno, la justicia y la hospitalidad",
        symbols="El rayo, el águila y el roble",
        questions=(
            "¿Cómo se salvó Zeus de ser devorado por su padre Crono?",
            "¿Cómo derrotó Zeus a los titanes?",
            "¿Cómo se repartieron Zeus y sus hermanos el mundo?",
            "¿Por qué castigó Zeus a Prometeo?",
        ),
    ),
    Character(
        "hera", "Hera", "Ἥρα", "ΗΡ", "Reina de los dioses", "Diosa olímpica",
        parents="Crono y Rea", domains="El matrimonio y las mujeres",
        symbols="El pavo real, la granada y la diadema",
        questions=(
            "¿Quién es Hera y cuáles son sus dominios?",
            "¿Qué le ocurrió a Hera nada más nacer?",
            "¿Por qué perseguía Hera a Heracles?",
            "¿Quiénes son los hijos de Hera y Zeus?",
        ),
    ),
    Character(
        "poseidon", "Poseidón", "Ποσειδῶν", "ΠΟ", "Señor de los mares", "Dios olímpico",
        parents="Crono y Rea", domains="El mar, los terremotos y los caballos",
        symbols="El tridente, el caballo y el delfín",
        questions=(
            "¿Por qué le correspondió el mar a Poseidón?",
            "¿Qué relación tenía Poseidón con el cíclope Polifemo?",
            "¿Qué tuvieron que ver Poseidón y Medusa con el nacimiento de Pegaso?",
            "¿Cuáles son los símbolos y dominios de Poseidón?",
        ),
    ),
    Character(
        "atenea", "Atenea", "Ἀθηνᾶ", "ΑΘ", "Sabiduría y estrategia", "Diosa olímpica",
        parents="Zeus y Metis", domains="La sabiduría, la guerra estratégica y los oficios",
        symbols="La lechuza, el olivo y la égida",
        questions=(
            "¿Cómo nació Atenea?",
            "¿Cómo ayudó Atenea a Aquiles a vencer a Héctor?",
            "¿Qué papel tuvo Atenea en la hazaña de Perseo?",
            "¿Por qué la cabeza de Medusa acabó en la égida de Atenea?",
        ),
    ),
    Character(
        "hades", "Hades", "ᾍδης", "ΑΔ", "Señor del inframundo", "Dios del inframundo",
        parents="Crono y Rea", domains="El mundo de los muertos y las riquezas del subsuelo",
        symbols="El casco de la invisibilidad, Cerbero y el ciprés",
        questions=(
            "¿Cómo se convirtió Hades en señor del inframundo?",
            "¿Cómo raptó Hades a Perséfone?",
            "¿Cómo convenció Orfeo a Hades para que le devolviera a Eurídice?",
            "¿Quiénes son los hermanos de Hades?",
        ),
    ),
    Character(
        "persefone", "Perséfone", "Περσεφόνη", "ΠΕ", "Reina de las sombras", "Diosa del inframundo",
        parents="Zeus y Deméter", domains="El inframundo y el regreso de la primavera",
        symbols="La granada, la antorcha y las espigas",
        questions=(
            "¿Por qué Perséfone pasa parte del año en el inframundo?",
            "¿Qué relación tiene el mito de Perséfone con las estaciones?",
            "¿Quiénes son los padres de Perséfone?",
            "¿Qué papel tuvo Perséfone en el mito de Orfeo?",
        ),
    ),
    Character(
        "prometeo", "Prometeo", "Προμηθεύς", "ΠΡ", "El que robó el fuego", "Titán",
        parents="Jápeto y Clímene", domains="La previsión y la protección de los humanos",
        symbols="El fuego y el tallo de hinojo",
        questions=(
            "¿Cómo robó Prometeo el fuego a los dioses?",
            "¿Qué castigo le impuso Zeus a Prometeo?",
            "¿Qué relación hay entre Prometeo y Pandora?",
            "¿Qué papel tuvo Prometeo en la creación del hombre?",
        ),
    ),
    Character(
        "crono", "Crono", "Κρόνος", "ΚΡ", "El titán que devoró a sus hijos", "Titán",
        parents="Urano y Gea", domains="Rey de los titanes y de la Edad de Oro",
        symbols="La hoz",
        questions=(
            "¿Cómo llegó Crono al poder?",
            "¿Por qué Crono devoraba a sus hijos?",
            "¿Cómo engañó Rea a Crono para salvar a Zeus?",
            "¿Qué fue la Titanomaquia y cómo terminó?",
        ),
    ),
    Character(
        "heracles", "Heracles", "Ἡρακλῆς", "ΗΚ", "El héroe de los doce trabajos", "Héroe",
        parents="Zeus y la mortal Alcmena", domains="La fuerza y la protección frente a los monstruos",
        symbols="La clava y la piel del león de Nemea",
        questions=(
            "¿Qué hizo Heracles siendo todavía un bebé?",
            "¿Por qué Hera odiaba a Heracles?",
            "¿Por qué tuvo que realizar Heracles sus trabajos?",
            "¿Cómo venció Heracles a la Hidra de Lerna?",
        ),
    ),
    Character(
        "perseo", "Perseo", "Περσεύς", "ΠΣ", "Matador de la gorgona", "Héroe",
        parents="Zeus y la mortal Dánae", domains="Vencedor de Medusa y salvador de Andrómeda",
        symbols="La cabeza de Medusa, las sandalias aladas y el escudo pulido",
        questions=(
            "¿Por qué Perseo y su madre fueron arrojados al mar en un cofre?",
            "¿Por qué el rey Polidectes envió a Perseo a por la cabeza de Medusa?",
            "¿Qué ayuda recibió Perseo de los dioses?",
            "¿Cómo derrotó Perseo a Medusa?",
        ),
    ),
    Character(
        "orfeo", "Orfeo", "Ὀρφεύς", "ΟΡ", "El cantor que bajó al Hades", "Héroe y poeta",
        parents="La musa Calíope y Apolo (o el rey Eagro, según otras versiones)",
        domains="La música y la poesía", symbols="La lira",
        questions=(
            "¿Qué poder tenía la música de Orfeo?",
            "¿Cómo murió Eurídice?",
            "¿Cómo convenció Orfeo a los dioses del inframundo?",
            "¿Por qué Orfeo perdió a Eurídice para siempre?",
        ),
    ),
    Character(
        "odiseo", "Odiseo", "Ὀδυσσεύς", "ΟΔ", "El de muchos ardides", "Héroe",
        parents="Laertes y Anticlea", domains="Rey de Ítaca, célebre por su astucia (mētis)",
        symbols="El arco y la nave",
        questions=(
            "¿Qué papel tuvo Odiseo en el caballo de Troya?",
            "¿Por qué Odiseo le dijo a Polifemo que se llamaba «Nadie»?",
            "¿Cómo escapó Odiseo de la cueva del cíclope?",
            "¿Cómo superó Odiseo el canto de las sirenas?",
        ),
    ),
)

CHARACTERS_BY_SLUG = {character.slug: character for character in PANTHEON}

# Pregunta con la que el agente genera la presentación de cada ficha (con RAG).
# Padres, dominios y símbolos ya están en la ficha: se pide solo lo narrativo, que es
# lo que la base de conocimiento cubre bien (así no hay que salir de las fuentes).
PRESENTATION_PROMPT = (
    "Presenta a {name} y resume sus mitos más importantes según tus fuentes, en dos "
    "párrafos breves. No menciones sus padres, dominios ni símbolos, y no comentes "
    "qué fuentes tienes o te faltan: cuenta solo lo que sabes."
)

# Las preguntas libres desde una ficha llevan el personaje delante para que el
# agente (y la búsqueda) sepan de quién se habla.
FREE_QUESTION_TEMPLATE = "Sobre {name}: {question}"


# ── Tipos de fuente (triangulación) ──────────────────────────────────────────

@dataclass(frozen=True)
class SourceKind:
    name: str          # debe coincidir con el metadato «Tipo» del corpus
    numeral: str
    summary: str
    works: str


SOURCE_KINDS: tuple[SourceKind, ...] = (
    SourceKind("Fuente primaria", "Α", "La voz de los propios griegos.", "Homero · Hesíodo"),
    SourceKind("Manual clásico", "Β", "Los mitos narrados con orden.", "Bulfinch, 1855"),
    SourceKind("Enciclopedia", "Γ", "Síntesis y contexto moderno.", "Wikipedia"),
)


# ── Árboles genealógicos ─────────────────────────────────────────────────────
# Solo parentescos. Las parejas son nodos propios («Zeus ⚭ Hera») de los que
# cuelgan los hijos; las versiones alternativas van en línea discontinua.

_GOLD, _MARBLE, _MUTED, _NODE, _COUPLE = "#b99b5e", "#e8e0cc", "#9c937e", "#121726", "#221d14"


def _dot(body: str, rankdir: str = "TB") -> str:
    return f"""
digraph {{
    graph [bgcolor="transparent", rankdir={rankdir}, nodesep=0.35, ranksep=0.55, fontname="Georgia"];
    node  [shape=box, style="rounded,filled", fillcolor="{_NODE}", color="{_GOLD}", penwidth=1.4,
           fontcolor="{_MARBLE}", fontname="Georgia", fontsize=13, margin="0.18,0.08"];
    edge  [color="{_GOLD}", penwidth=1.3, arrowsize=0.6];
{body}
}}"""


def _couple(node_id: str, label: str) -> str:
    return (
        f'    {node_id} [label="{label}", fillcolor="{_COUPLE}", fontcolor="{_GOLD}", '
        f'fontsize=12, style="rounded,filled,dashed"];\n'
    )


def _member(person: str, couple: str) -> str:
    """Línea punteada sin flecha: la persona forma parte de esa pareja."""
    return f'    {person} -> {couple} [dir=none, style=dotted, color="{_MUTED}", penwidth=1.6];\n'


def _alternative(source: str, target: str, label: str) -> str:
    return (
        f'    {source} -> {target} [style=dashed, color="{_MUTED}", label="  {label}", '
        f'fontcolor="{_MUTED}", fontsize=10];\n'
    )


@dataclass(frozen=True)
class FamilyTree:
    title: str
    description: str
    dot: str
    stretch: bool = True  # False: tamaño natural (árboles muy altos)


FAMILY_TREES: tuple[FamilyTree, ...] = (
    FamilyTree(
        title="Orígenes",
        description="Del Caos a los titanes, según la Teogonía de Hesíodo.",
        dot=_dot(
            '    Caos [shape=ellipse, fontcolor="#b99b5e"]; Gea [shape=ellipse, fontcolor="#b99b5e"];\n'
            "    { rank=same; Caos; Gea; }\n"
            "    Caos -> Érebo; Caos -> Nix;\n"
            "    Gea -> Urano;\n"
            + _couple("gea_urano", "Gea ⚭ Urano")
            + _member("Gea", "gea_urano")
            + _member("Urano", "gea_urano")
            + "    gea_urano -> { Crono Rea Océano Jápeto Mnemósine Hiperión };\n"
            '    gea_urano -> cyclopes; cyclopes [label="Cíclopes"];\n'
            '    gea_urano -> hecatonchires; hecatonchires [label="Hecatónquiros"];\n'
            + _couple("japeto_climene", "Jápeto ⚭ Clímene")
            + _member("Jápeto", "japeto_climene")
            + "    japeto_climene -> { Prometeo Epimeteo Atlas };\n"
            + _alternative("Urano", "Afrodita", "según Hesíodo, de la espuma del mar")
        ),
    ),
    FamilyTree(
        title="Olímpicos",
        description="Los seis hijos de Crono y Rea, que derrocaron a los titanes y se repartieron el mundo.",
        dot=_dot(
            "    Crono; Rea; { rank=same; Crono; Rea; }\n"
            + _couple("crono_rea", "Crono ⚭ Rea")
            + _member("Crono", "crono_rea") + _member("Rea", "crono_rea")
            + '    crono_rea -> hestia;   hestia   [label="Hestia\\nhogar"];\n'
            '    crono_rea -> demeter;  demeter  [label="Deméter\\nagricultura"];\n'
            '    crono_rea -> hera;     hera     [label="Hera\\nmatrimonio"];\n'
            '    crono_rea -> hades;    hades    [label="Hades\\ninframundo"];\n'
            '    crono_rea -> poseidon; poseidon [label="Poseidón\\nmar"];\n'
            '    crono_rea -> zeus;     zeus     [label="Zeus\\ncielo", penwidth=2.4, fontcolor="#e8e0cc"];\n'
        ),
    ),
    FamilyTree(
        title="Descendencia de Zeus",
        description="Hijos de Zeus con diosas, titánides y mortales.",
        dot=_dot(
            '    Zeus [penwidth=2.4, fontcolor="#e8e0cc"];\n'
            + "".join(_member("Zeus", c) for c in (
                "z_hera", "z_metis", "z_leto", "z_maya", "z_demeter",
                "z_mnemosine", "z_semele", "z_danae", "z_alcmena", "z_dione",
            ))
            + _couple("z_hera", "Zeus ⚭ Hera")
            + "    z_hera -> { Ares Hebe };\n"
            + _alternative("z_hera", "Hefesto", "según Homero; en Hesíodo, solo de Hera")
            + _couple("z_metis", "Zeus ⚭ Metis") + "    z_metis -> Atenea;\n"
            + _couple("z_leto", "Zeus ⚭ Leto") + "    z_leto -> { Apolo Artemisa };\n"
            + _couple("z_maya", "Zeus ⚭ Maya") + "    z_maya -> Hermes;\n"
            + _couple("z_demeter", "Zeus ⚭ Deméter") + "    z_demeter -> Perséfone;\n"
            + _couple("z_mnemosine", "Zeus ⚭ Mnemósine") + '    z_mnemosine -> musas; musas [label="Las nueve Musas"];\n'
            + _couple("z_semele", "Zeus ⚭ Sémele") + "    z_semele -> Dioniso;\n"
            + _couple("z_danae", "Zeus ⚭ Dánae") + "    z_danae -> Perseo;\n"
            + _couple("z_alcmena", "Zeus ⚭ Alcmena") + "    z_alcmena -> Heracles;\n"
            + _couple("z_dione", "Zeus ⚭ Dione")
            + _alternative("z_dione", "Afrodita", "según Homero"),
            rankdir="LR",
        ),
        stretch=False,
    ),
)

GENEALOGY_LEGEND_HTML = (
    "<b>Cómo leer los árboles</b> · Los recuadros de borde discontinuo son <b>parejas</b>: la línea "
    "<b>punteada</b> une a cada miembro con su pareja, y de la pareja cuelgan los hijos con "
    "<b>flechas doradas</b> (filiación). Las <b>flechas grises discontinuas</b> marcan una "
    "<b>versión alternativa</b> del mito, con el autor que la recoge."
)
