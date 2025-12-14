from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from db.neo4j.neo4j_handler import query_graph
from db.vector.rag_pipeline import build_context_bundle, build_prompt, llm_generate

_TAG_KEYWORDS = (
    "tag",
    "tags",
    "genero",
    "generos",
    "género",
    "géneros",
    "genre",
    "genres",
)
_ARTIST_KEYWORDS = ("artista", "artistas", "artist", "artists")
_TERMS_AFTER = (
    r"son",
    r"es",
    r"se\s+llaman",
    r"llamados",
    r"llamadas",
    r"pertenecen\s+a",
    r"relacionados\s+con",
    r"etiquetados\s+como",
)


@dataclass(slots=True)
class ArtistTagMatch:
    node_id: str
    artist_name: str
    matched_terms: List[str]
    tags: List[str]
    genres: List[str]

    def as_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "artist_name": self.artist_name,
            "matched_terms": self.matched_terms,
            "tags": self.tags,
            "genres": self.genres,
        }


@dataclass(slots=True)
class QueryEngineResult:
    answer: str
    context: List[str]
    tag_term: Optional[str] = None
    tag_matches: List[ArtistTagMatch] = field(default_factory=list)
    debug: Optional["QueryDebugInfo"] = None


@dataclass(slots=True)
class QueryDebugInfo:
    prompt: str
    vector_hits: List[Dict[str, object]]
    graph_context: List[str]
    context_sections: List[str]
    tag_term: Optional[str]


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


def _clean_term(value: str) -> str:
    cleaned = value.strip().strip("¿?¡!.,:;\"'()[]")
    return cleaned.strip()


def _has_keywords(text: str, keywords: tuple[str, ...]) -> bool:
    folded = _strip_accents(text)
    return any(keyword in folded for keyword in keywords)


def _extract_quoted_term(question: str) -> Optional[str]:
    quoted = re.findall(r"['\"]([^'\"]+)['\"]", question)
    for candidate in quoted:
        candidate = _clean_term(candidate)
        if candidate:
            return candidate
    return None


def detect_artist_tag_term(question: str) -> Optional[str]:
    if not _has_keywords(question, _TAG_KEYWORDS):
        return None
    if not _has_keywords(question, _ARTIST_KEYWORDS):
        return None

    quoted = _extract_quoted_term(question)
    if quoted:
        return quoted

    pattern = re.compile(
        rf"(?:{'|'.join(_TERMS_AFTER)})\s+([a-zA-Z0-9ÁÉÍÓÚÜÑáéíóúüñ\- ]+)",
        re.IGNORECASE,
    )
    match = pattern.search(question)
    if match:
        candidate = _clean_term(match.group(1))
        if candidate:
            return candidate

    tokens = question.strip().split()
    if tokens:
        candidate = _clean_term(tokens[-1])
        if candidate:
            return candidate
    return None


def fetch_artists_by_tag(term: str, limit: int = 25) -> List[ArtistTagMatch]:
    cypher = """
        MATCH (a:Artist)-[rel]->(label)
        WHERE any(l IN labels(label) WHERE l IN ['Tag', 'Genre'])
            AND toLower(label.name) CONTAINS toLower($term)
    WITH DISTINCT a, collect(DISTINCT label) AS matched_nodes
    OPTIONAL MATCH (a)-[tag_rel]->(tag:Tag)
    WITH a, matched_nodes, collect(DISTINCT tag.name) AS tags
        OPTIONAL MATCH (a)-[genre_rel]->(genre)
        WHERE 'Genre' IN labels(genre)
        WITH a, matched_nodes, tags, collect(DISTINCT genre.name) AS genres
    RETURN elementId(a) AS node_id,
        a.name AS artist_name,
        [node IN matched_nodes WHERE node.name IS NOT NULL | node.name] AS matched_terms,
        [tag_name IN tags WHERE tag_name IS NOT NULL | tag_name] AS tags,
        [genre_name IN genres WHERE genre_name IS NOT NULL | genre_name] AS genres
    ORDER BY artist_name
    LIMIT $limit
    """

    rows = query_graph(cypher, {"term": term, "limit": limit})

    matches: List[ArtistTagMatch] = []
    for row in rows:
        node_id = row.get("node_id")
        artist_name = row.get("artist_name")
        if not node_id or not artist_name:
            continue
        matches.append(
            ArtistTagMatch(
                node_id=node_id,
                artist_name=artist_name,
                matched_terms=sorted(
                    {t for t in (row.get("matched_terms") or []) if t}
                ),
                tags=sorted({t for t in (row.get("tags") or []) if t}),
                genres=sorted({g for g in (row.get("genres") or []) if g}),
            )
        )
    return matches


def _format_artist_tag_context(term: str, matches: List[ArtistTagMatch]) -> str:
    lines = [
        f"Artistas encontrados para el tag/género '{term}':",
    ]
    for match in matches:
        tags = ", ".join(match.tags) if match.tags else "(sin tags)"
        genres = ", ".join(match.genres) if match.genres else "(sin géneros)"
        lines.append(f"- {match.artist_name} | tags: {tags} | géneros: {genres}")
    return "\n".join(lines)


def run_semantic_query(
    question: str, top_k: int = 8, include_debug: bool = False
) -> QueryEngineResult:
    top_k = max(1, min(top_k, 20))

    tag_term = detect_artist_tag_term(question)
    tag_matches: List[ArtistTagMatch] = []
    context_sections: List[str] = []

    if tag_term:
        tag_matches = fetch_artists_by_tag(tag_term)
        if tag_matches:
            context_sections.append(_format_artist_tag_context(tag_term, tag_matches))

    bundle = build_context_bundle(question, top_k)
    context_sections.extend(bundle.full_context)

    if not context_sections:
        context_sections = [
            "No se recuperó contexto de Neo4j ni Milvus para esta pregunta."
        ]

    prompt = build_prompt(question, context_sections)
    answer = llm_generate(prompt)

    debug_info = None
    if include_debug:
        debug_info = QueryDebugInfo(
            prompt=prompt,
            vector_hits=bundle.vector_hits,
            graph_context=bundle.graph_context,
            context_sections=context_sections,
            tag_term=tag_term,
        )

    return QueryEngineResult(
        answer=answer,
        context=context_sections,
        tag_term=tag_term,
        tag_matches=tag_matches,
        debug=debug_info,
    )
