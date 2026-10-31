"""What a template section waits for before it shows: confirmed facts, and media D-SAP has supplied.

A gate in templates.json is a fact id, or media:{slot id} for a media slot. A slot whose origin is
"awaited" holds the section back until D-SAP adds the file (docs/setup/media-to-add.md).
"""

from __future__ import annotations

from ..site.model import Site
from .model import Content, SectionSpec

MEDIA_PREFIX = "media:"
NOT_READY = {"awaited"}


def section_waiting(spec: SectionSpec, content: Content, site: Site) -> tuple[list[str], list[str]]:
    """(gates still waiting, gates that name nothing known)."""
    waiting, unknown = [], []
    for gate in spec.gates:
        if gate.startswith(MEDIA_PREFIX):
            origin = content.media.get(gate.removeprefix(MEDIA_PREFIX))
            if origin is None:
                unknown.append(gate)
            elif origin in NOT_READY:
                waiting.append(gate)
        elif gate not in site.facts:
            unknown.append(gate)
        elif not site.facts[gate].confirmed:
            waiting.append(gate)
    return waiting, unknown
