"""
Perfil del dominio.

Es el ÚNICO punto que hay que cambiar para convertir el asistente en experto de
otro tema: nuevos documentos en data/, un nuevo DomainProfile y listo. El motor
(knowledge_base.py, agent.py) no sabe nada de mitología.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.prompts import SYSTEM_PROMPT


@dataclass(frozen=True)
class DomainProfile:
    domain_name: str
    assistant_name: str
    collection_name: str
    system_prompt: str
    welcome_message: str
    example_questions: tuple[str, ...]


GREEK_MYTHOLOGY = DomainProfile(
    domain_name="Mitología griega",
    assistant_name="Mnemósine",
    collection_name="greek_mythology",
    system_prompt=SYSTEM_PROMPT,
    welcome_message=(
        "Soy Mnemósine, titánide de la memoria y madre de las Musas. "
        "Guardo los mitos de dioses, titanes, héroes y monstruos. ¿Qué deseas recordar?"
    ),
    example_questions=(
        "¿Cómo derrotó Perseo a Medusa?",
        "¿Por qué castigó Zeus a Prometeo?",
        "¿Cuáles fueron los doce trabajos de Heracles?",
        "¿Qué fue el caballo de Troya y quién lo ideó?",
        "¿Cómo llegaron los olímpicos al poder?",
    ),
)

ACTIVE_DOMAIN = GREEK_MYTHOLOGY
