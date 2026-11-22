"""Source registry and citation handling.

Source numbers are global to a conversation, so a citation like [3] keeps
pointing at the same document across turns.
"""

import re
from dataclasses import dataclass

CITATION_RE = re.compile(r"\[(\d{1,3})\]")


@dataclass
class Source:
    id: int
    title: str
    url: str
    kind: str  # "web" or "local"


class SourceRegistry:
    def __init__(self):
        self._sources: list[Source] = []
        self._by_key: dict[str, Source] = {}

    def add(self, title: str, url: str, kind: str = "web") -> Source:
        if url in self._by_key:
            return self._by_key[url]
        src = Source(id=len(self._sources) + 1, title=title or url, url=url, kind=kind)
        self._sources.append(src)
        self._by_key[url] = src
        return src

    def get(self, source_id: int) -> Source | None:
        if 1 <= source_id <= len(self._sources):
            return self._sources[source_id - 1]
        return None

    def all(self) -> list[Source]:
        return list(self._sources)


def extract_citations(text: str, registry: SourceRegistry) -> tuple[str, list[Source]]:
    """Verify citation markers against real sources.

    Markers that point at unknown sources are removed, so the model cannot
    cite a source it never retrieved. Returns cleaned text and the cited
    sources in order of first appearance.
    """
    # Normalize alternative bracket and citation formats (e.g. 【1】, 【1†source】) to standard [1]
    text = re.sub(r"[【\[](\d{1,3})(?:[†:].*?)?[】\]]", r"[\1]", text)

    cited: list[Source] = []

    def _replace(match: re.Match) -> str:
        src = registry.get(int(match.group(1)))
        if src is None:
            return ""
        if src.id not in {s.id for s in cited}:
            cited.append(src)
        return match.group(0)

    cleaned = CITATION_RE.sub(_replace, text)
    cleaned = re.sub(r"[ \t]+([.,;:])", r"\1", cleaned)  # tidy spaces left before punctuation
    cleaned = re.sub(r"  +", " ", cleaned)
    return cleaned, cited
