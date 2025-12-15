from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from db.neo4j.neo4j_handler import query_graph
from db.vector.rag_pipeline import build_context_bundle, build_prompt, llm_generate

# =============================================================================
# KEYWORD DEFINITIONS FOR QUERY DETECTION
# =============================================================================

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

# Keywords for song/recording queries
_SONG_KEYWORDS = (
    "cancion",
    "canciones",
    "canción",
    "song",
    "songs",
    "track",
    "tracks",
    "tema",
    "temas",
    "recording",
    "recordings",
    "pista",
    "pistas",
)

# Keywords for album/release queries
_ALBUM_KEYWORDS = (
    "album",
    "albums",
    "álbum",
    "álbumes",
    "disco",
    "discos",
    "release",
    "releases",
    "lanzamiento",
    "lanzamientos",
)

# Keywords for similar/related queries
_SIMILAR_KEYWORDS = (
    "similar",
    "similares",
    "parecido",
    "parecidos",
    "parecida",
    "parecidas",
    "como",
    "estilo",
    "related",
    "relacionado",
    "relacionados",
)

# Keywords for popular/top queries
_POPULAR_KEYWORDS = (
    "popular",
    "populares",
    "famoso",
    "famosos",
    "famosa",
    "famosas",
    "top",
    "mejor",
    "mejores",
    "best",
    "conocido",
    "conocidos",
    "conocida",
    "conocidas",
)

# Keywords for collaboration queries
_COLLAB_KEYWORDS = (
    "colaboracion",
    "colaboraciones",
    "colaboración",
    "featuring",
    "feat",
    "ft",
    "junto",
    "juntos",
    "with",
    "collaboration",
    "collaborations",
    "trabaja",
    "trabajado",
)

# Keywords for area/location queries
_AREA_KEYWORDS = (
    "pais",
    "país",
    "ciudad",
    "region",
    "región",
    "lugar",
    "country",
    "city",
    "area",
    "location",
    "from",
    "de donde",
    "origen",
)

_TERMS_AFTER = (
    r"son",
    r"es",
    r"se\s+llaman",
    r"llamados",
    r"llamadas",
    r"pertenecen\s+a",
    r"relacionados\s+con",
    r"etiquetados\s+como",
    r"de",
    r"by",
    r"por",
    r"titulada",
    r"titled",
    r"called",
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
class SongMatch:
    """Represents a song/recording match from the database."""
    node_id: str
    song_name: str
    artist_name: Optional[str]
    album_name: Optional[str]
    duration_ms: Optional[int]
    tags: List[str]

    def as_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "song_name": self.song_name,
            "artist_name": self.artist_name,
            "album_name": self.album_name,
            "duration_ms": self.duration_ms,
            "duration_formatted": self._format_duration(),
            "tags": self.tags,
        }

    def _format_duration(self) -> str:
        if not self.duration_ms:
            return "N/A"
        seconds = self.duration_ms // 1000
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}:{secs:02d}"


@dataclass(slots=True)
class AlbumMatch:
    """Represents an album/release match from the database."""
    node_id: str
    album_name: str
    artist_name: Optional[str]
    release_date: Optional[str]
    track_count: int
    tags: List[str]

    def as_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "album_name": self.album_name,
            "artist_name": self.artist_name,
            "release_date": self.release_date,
            "track_count": self.track_count,
            "tags": self.tags,
        }


@dataclass(slots=True)
class ArtistMatch:
    """Represents an artist match with full details."""
    node_id: str
    artist_name: str
    area: Optional[str]
    begin_date: Optional[str]
    end_date: Optional[str]
    artist_type: Optional[str]
    tags: List[str]
    genres: List[str]
    album_count: int
    song_count: int

    def as_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "artist_name": self.artist_name,
            "area": self.area,
            "begin_date": self.begin_date,
            "end_date": self.end_date,
            "artist_type": self.artist_type,
            "tags": self.tags,
            "genres": self.genres,
            "album_count": self.album_count,
            "song_count": self.song_count,
        }


@dataclass(slots=True)
class CollaborationMatch:
    """Represents a collaboration between artists."""
    artist1_name: str
    artist2_name: str
    recording_name: str
    recording_id: str

    def as_dict(self) -> dict:
        return {
            "artist1_name": self.artist1_name,
            "artist2_name": self.artist2_name,
            "recording_name": self.recording_name,
            "recording_id": self.recording_id,
        }


@dataclass(slots=True)
class QueryEngineResult:
    answer: str
    context: List[str]
    query_type: str = "general"
    tag_term: Optional[str] = None
    tag_matches: List[ArtistTagMatch] = field(default_factory=list)
    song_matches: List[SongMatch] = field(default_factory=list)
    album_matches: List[AlbumMatch] = field(default_factory=list)
    artist_matches: List[ArtistMatch] = field(default_factory=list)
    collaboration_matches: List[CollaborationMatch] = field(default_factory=list)
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


# =============================================================================
# SONG/RECORDING SEARCH FUNCTIONS
# =============================================================================

def detect_song_query(question: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Detect if the question is about songs/recordings.
    Returns: (is_song_query, song_term, artist_term)
    """
    if not _has_keywords(question, _SONG_KEYWORDS):
        return False, None, None

    song_term = _extract_quoted_term(question)
    artist_term = None

    # Try to extract artist name if mentioned
    if _has_keywords(question, _ARTIST_KEYWORDS):
        # Look for patterns like "canciones de [artist]" or "songs by [artist]"
        artist_pattern = re.compile(
            r"(?:de|by|por|del artista|from)\s+['\"]?([a-zA-Z0-9ÁÉÍÓÚÜÑáéíóúüñ\s\-]+)['\"]?",
            re.IGNORECASE,
        )
        match = artist_pattern.search(question)
        if match:
            artist_term = _clean_term(match.group(1))

    return True, song_term, artist_term


def fetch_songs_by_name(term: str, limit: int = 25) -> List[SongMatch]:
    """Search for songs/recordings by name."""
    cypher = """
    MATCH (r:Recording)
    WHERE toLower(r.name) CONTAINS toLower($term)
    OPTIONAL MATCH (a:Artist)-[:PERFORMED_ON]->(r)
    OPTIONAL MATCH (r)-[:HAS_TAG]->(t:Tag)
    WITH r, 
         collect(DISTINCT a.name)[0] AS artist_name,
         collect(DISTINCT t.name) AS tags
    RETURN elementId(r) AS node_id,
           r.name AS song_name,
           artist_name,
           null AS album_name,
           r.length AS duration_ms,
           [t IN tags WHERE t IS NOT NULL | t] AS tags
    ORDER BY r.name
    LIMIT $limit
    """
    rows = query_graph(cypher, {"term": term, "limit": limit})

    matches: List[SongMatch] = []
    for row in rows:
        node_id = row.get("node_id")
        song_name = row.get("song_name")
        if not node_id or not song_name:
            continue
        matches.append(
            SongMatch(
                node_id=node_id,
                song_name=song_name,
                artist_name=row.get("artist_name"),
                album_name=row.get("album_name"),
                duration_ms=row.get("duration_ms"),
                tags=sorted({t for t in (row.get("tags") or []) if t}),
            )
        )
    return matches


def fetch_songs_by_artist(artist_name: str, limit: int = 25) -> List[SongMatch]:
    """Search for songs/recordings by artist name."""
    cypher = """
    MATCH (a:Artist)-[:PERFORMED_ON]->(r:Recording)
    WHERE toLower(a.name) CONTAINS toLower($artist_name)
    OPTIONAL MATCH (r)-[:HAS_TAG]->(t:Tag)
    WITH r, a.name AS artist_name,
         collect(DISTINCT t.name) AS tags
    RETURN elementId(r) AS node_id,
           r.name AS song_name,
           artist_name,
           null AS album_name,
           r.length AS duration_ms,
           [t IN tags WHERE t IS NOT NULL | t] AS tags
    ORDER BY r.name
    LIMIT $limit
    """
    rows = query_graph(cypher, {"artist_name": artist_name, "limit": limit})

    matches: List[SongMatch] = []
    for row in rows:
        node_id = row.get("node_id")
        song_name = row.get("song_name")
        if not node_id or not song_name:
            continue
        matches.append(
            SongMatch(
                node_id=node_id,
                song_name=song_name,
                artist_name=row.get("artist_name"),
                album_name=row.get("album_name"),
                duration_ms=row.get("duration_ms"),
                tags=sorted({t for t in (row.get("tags") or []) if t}),
            )
        )
    return matches


def _format_song_context(matches: List[SongMatch], search_type: str = "nombre") -> str:
    lines = [f"Canciones encontradas por {search_type}:"]
    for match in matches:
        artist = match.artist_name or "Artista desconocido"
        album = match.album_name or "Álbum desconocido"
        duration = match._format_duration()
        tags = ", ".join(match.tags) if match.tags else "(sin tags)"
        lines.append(f"- {match.song_name} | Artista: {artist} | Álbum: {album} | Duración: {duration} | Tags: {tags}")
    return "\n".join(lines)


# =============================================================================
# SONGS BY GENRE/TAG SEARCH FUNCTIONS
# =============================================================================

def detect_songs_by_genre_query(question: str) -> Tuple[bool, Optional[str]]:
    """
    Detect if the question is asking for songs from artists of a specific genre/tag.
    Examples: "canciones de artistas de jazz", "mejores canciones de rock",
              "songs from jazz artists", "best songs by metal artists"
    Returns: (is_songs_by_genre_query, genre_term)
    """
    # Must mention songs AND (genre keywords OR be asking about artists with a genre)
    has_songs = _has_keywords(question, _SONG_KEYWORDS) or _has_keywords(question, _POPULAR_KEYWORDS + ("cancion", "canciones", "canción"))
    has_genre_context = _has_keywords(question, _TAG_KEYWORDS)
    has_artist_context = _has_keywords(question, _ARTIST_KEYWORDS)
    
    # Pattern: songs/canciones + artists/artistas + genre (e.g., "canciones de artistas de jazz")
    if has_songs and has_artist_context:
        # Extract the genre term
        pattern = re.compile(
            r"(?:artistas?|artists?)\s+(?:de|del?|of|from)\s+([a-zA-Z0-9ÁÉÍÓÚÜÑáéíóúüñ\s\-]+?)(?:\s+(?:y|and|with|con)\s+|$|,|\.|;)",
            re.IGNORECASE,
        )
        match = pattern.search(question)
        if match:
            genre_term = _clean_term(match.group(1))
            # Filter out common stop words
            stop_words = {"los", "las", "el", "la", "un", "una", "the", "a", "an"}
            if genre_term.lower() not in stop_words and len(genre_term) > 1:
                return True, genre_term
    
    # Pattern: genre + songs (e.g., "mejores canciones de jazz", "best rock songs")
    if has_songs and has_genre_context:
        quoted = _extract_quoted_term(question)
        if quoted:
            return True, quoted
        
        # Try to extract genre after "de" or similar
        pattern = re.compile(
            r"(?:canciones?|songs?|temas?)\s+(?:de|del?|of|from)\s+([a-zA-Z0-9ÁÉÍÓÚÜÑáéíóúüñ\s\-]+?)(?:\s+(?:y|and|with|con)\s+|$|,|\.|;)",
            re.IGNORECASE,
        )
        match = pattern.search(question)
        if match:
            genre_term = _clean_term(match.group(1))
            stop_words = {"los", "las", "el", "la", "un", "una", "the", "a", "an", "artistas", "artists"}
            if genre_term.lower() not in stop_words and len(genre_term) > 1:
                return True, genre_term
    
    return False, None


def fetch_songs_by_genre(genre_term: str, limit_artists: int = 10, limit_songs_per_artist: int = 3) -> List[SongMatch]:
    """
    Search for songs from artists that have a specific genre/tag.
    Returns songs grouped by artist.
    """
    cypher = """
    MATCH (a:Artist)-[rel]->(label)
    WHERE any(l IN labels(label) WHERE l IN ['Tag', 'Genre'])
        AND toLower(label.name) CONTAINS toLower($genre_term)
    WITH DISTINCT a
    LIMIT $limit_artists
    MATCH (a)-[:PERFORMED_ON]->(r:Recording)
    OPTIONAL MATCH (r)-[:HAS_TAG]->(t:Tag)
    WITH a, r, 
         collect(DISTINCT t.name) AS tags
    ORDER BY a.name, r.name
    WITH a, collect({
        node_id: elementId(r),
        song_name: r.name,
        album_name: null,
        duration_ms: r.length,
        tags: [t IN tags WHERE t IS NOT NULL | t]
    })[0..$limit_songs] AS songs
    UNWIND songs AS song
    RETURN song.node_id AS node_id,
           song.song_name AS song_name,
           a.name AS artist_name,
           song.album_name AS album_name,
           song.duration_ms AS duration_ms,
           song.tags AS tags
    """
    rows = query_graph(cypher, {
        "genre_term": genre_term, 
        "limit_artists": limit_artists,
        "limit_songs": limit_songs_per_artist
    })

    matches: List[SongMatch] = []
    for row in rows:
        node_id = row.get("node_id")
        song_name = row.get("song_name")
        if not node_id or not song_name:
            continue
        matches.append(
            SongMatch(
                node_id=node_id,
                song_name=song_name,
                artist_name=row.get("artist_name"),
                album_name=row.get("album_name"),
                duration_ms=row.get("duration_ms"),
                tags=sorted({t for t in (row.get("tags") or []) if t}),
            )
        )
    return matches


def _format_songs_by_genre_context(matches: List[SongMatch], genre_term: str) -> str:
    """Format song matches for artists of a specific genre."""
    lines = [f"Canciones de artistas del género/tag '{genre_term}':"]
    
    # Group by artist for better readability
    songs_by_artist: Dict[str, List[SongMatch]] = {}
    for match in matches:
        artist = match.artist_name or "Artista desconocido"
        if artist not in songs_by_artist:
            songs_by_artist[artist] = []
        songs_by_artist[artist].append(match)
    
    for artist, songs in songs_by_artist.items():
        lines.append(f"\n{artist}:")
        for song in songs:
            album = song.album_name or "Álbum desconocido"
            duration = song._format_duration()
            lines.append(f"  - {song.song_name} | Álbum: {album} | Duración: {duration}")
    
    return "\n".join(lines)


# =============================================================================
# ALBUM/RELEASE SEARCH FUNCTIONS
# =============================================================================

def detect_album_query(question: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Detect if the question is about albums/releases.
    Returns: (is_album_query, album_term, artist_term)
    """
    if not _has_keywords(question, _ALBUM_KEYWORDS):
        return False, None, None

    album_term = _extract_quoted_term(question)
    artist_term = None

    if _has_keywords(question, _ARTIST_KEYWORDS):
        artist_pattern = re.compile(
            r"(?:de|by|por|del artista|from)\s+['\"]?([a-zA-Z0-9ÁÉÍÓÚÜÑáéíóúüñ\s\-]+)['\"]?",
            re.IGNORECASE,
        )
        match = artist_pattern.search(question)
        if match:
            artist_term = _clean_term(match.group(1))

    return True, album_term, artist_term


def fetch_albums_by_name(term: str, limit: int = 25) -> List[AlbumMatch]:
    """Search for albums/releases by name."""
    cypher = """
    MATCH (rel:Release)
    WHERE toLower(rel.name) CONTAINS toLower($term)
    OPTIONAL MATCH (a:Artist)-[:RELEASED]->(rel)
    OPTIONAL MATCH (rel)-[:HAS_TAG]->(t:Tag)
    OPTIONAL MATCH (tr:Track)-[:APPEARS_ON]->(rel)
    WITH rel, 
         collect(DISTINCT a.name)[0] AS artist_name,
         collect(DISTINCT t.name) AS tags,
         count(DISTINCT tr) AS track_count
    RETURN elementId(rel) AS node_id,
           rel.name AS album_name,
           artist_name,
           rel.date AS release_date,
           track_count,
           [t IN tags WHERE t IS NOT NULL | t] AS tags
    ORDER BY rel.name
    LIMIT $limit
    """
    rows = query_graph(cypher, {"term": term, "limit": limit})

    matches: List[AlbumMatch] = []
    for row in rows:
        node_id = row.get("node_id")
        album_name = row.get("album_name")
        if not node_id or not album_name:
            continue
        matches.append(
            AlbumMatch(
                node_id=node_id,
                album_name=album_name,
                artist_name=row.get("artist_name"),
                release_date=row.get("release_date"),
                track_count=row.get("track_count", 0),
                tags=sorted({t for t in (row.get("tags") or []) if t}),
            )
        )
    return matches


def fetch_albums_by_artist(artist_name: str, limit: int = 25) -> List[AlbumMatch]:
    """Search for albums/releases by artist name."""
    cypher = """
    MATCH (a:Artist)-[:RELEASED]->(rel:Release)
    WHERE toLower(a.name) CONTAINS toLower($artist_name)
    OPTIONAL MATCH (rel)-[:HAS_TAG]->(t:Tag)
    OPTIONAL MATCH (tr:Track)-[:APPEARS_ON]->(rel)
    WITH rel, a.name AS artist_name,
         collect(DISTINCT t.name) AS tags,
         count(DISTINCT tr) AS track_count
    RETURN elementId(rel) AS node_id,
           rel.name AS album_name,
           artist_name,
           rel.date AS release_date,
           track_count,
           [t IN tags WHERE t IS NOT NULL | t] AS tags
    ORDER BY rel.date DESC, rel.name
    LIMIT $limit
    """
    rows = query_graph(cypher, {"artist_name": artist_name, "limit": limit})

    matches: List[AlbumMatch] = []
    for row in rows:
        node_id = row.get("node_id")
        album_name = row.get("album_name")
        if not node_id or not album_name:
            continue
        matches.append(
            AlbumMatch(
                node_id=node_id,
                album_name=album_name,
                artist_name=row.get("artist_name"),
                release_date=row.get("release_date"),
                track_count=row.get("track_count", 0),
                tags=sorted({t for t in (row.get("tags") or []) if t}),
            )
        )
    return matches


def _format_album_context(matches: List[AlbumMatch], search_type: str = "nombre") -> str:
    lines = [f"Álbumes encontrados por {search_type}:"]
    for match in matches:
        artist = match.artist_name or "Artista desconocido"
        date = match.release_date or "Fecha desconocida"
        tags = ", ".join(match.tags) if match.tags else "(sin tags)"
        lines.append(f"- {match.album_name} | Artista: {artist} | Fecha: {date} | Tracks: {match.track_count} | Tags: {tags}")
    return "\n".join(lines)


# =============================================================================
# ARTIST DETAIL SEARCH FUNCTIONS
# =============================================================================

def detect_artist_detail_query(question: str) -> Tuple[bool, Optional[str]]:
    """
    Detect if the question is asking for details about a specific artist.
    Returns: (is_artist_query, artist_term)
    """
    if not _has_keywords(question, _ARTIST_KEYWORDS):
        return False, None

    # Avoid overlap with tag queries
    if _has_keywords(question, _TAG_KEYWORDS):
        return False, None

    artist_term = _extract_quoted_term(question)
    if not artist_term:
        # Try to extract after common patterns
        pattern = re.compile(
            r"(?:artista|artist|sobre|about|quien es|who is|información de|info about)\s+['\"]?([a-zA-Z0-9ÁÉÍÓÚÜÑáéíóúüñ\s\-]+)['\"]?",
            re.IGNORECASE,
        )
        match = pattern.search(question)
        if match:
            artist_term = _clean_term(match.group(1))

    return bool(artist_term), artist_term


def fetch_artist_details(artist_name: str, limit: int = 10) -> List[ArtistMatch]:
    """Get detailed information about artists matching the name."""
    cypher = """
    MATCH (a:Artist)
    WHERE toLower(a.name) CONTAINS toLower($artist_name)
    OPTIONAL MATCH (a)-[:FROM_AREA]->(area:Area)
    OPTIONAL MATCH (a)-[:HAS_TAG]->(t:Tag)
    OPTIONAL MATCH (a)-[:HAS_TAG]->(g:Genre)
    OPTIONAL MATCH (a)-[:RELEASED]->(rel:Release)
    OPTIONAL MATCH (a)-[:PERFORMED_ON]->(rec:Recording)
    WITH a, area,
         collect(DISTINCT t.name) AS tags,
         collect(DISTINCT g.name) AS genres,
         count(DISTINCT rel) AS album_count,
         count(DISTINCT rec) AS song_count
    RETURN elementId(a) AS node_id,
           a.name AS artist_name,
           area.name AS area,
           a.begin_date AS begin_date,
           a.end_date AS end_date,
           a.type AS artist_type,
           [t IN tags WHERE t IS NOT NULL | t] AS tags,
           [g IN genres WHERE g IS NOT NULL | g] AS genres,
           album_count,
           song_count
    ORDER BY song_count DESC
    LIMIT $limit
    """
    rows = query_graph(cypher, {"artist_name": artist_name, "limit": limit})

    matches: List[ArtistMatch] = []
    for row in rows:
        node_id = row.get("node_id")
        name = row.get("artist_name")
        if not node_id or not name:
            continue
        matches.append(
            ArtistMatch(
                node_id=node_id,
                artist_name=name,
                area=row.get("area"),
                begin_date=row.get("begin_date"),
                end_date=row.get("end_date"),
                artist_type=row.get("artist_type"),
                tags=sorted({t for t in (row.get("tags") or []) if t}),
                genres=sorted({g for g in (row.get("genres") or []) if g}),
                album_count=row.get("album_count", 0),
                song_count=row.get("song_count", 0),
            )
        )
    return matches


def _format_artist_detail_context(matches: List[ArtistMatch]) -> str:
    lines = ["Información de artistas encontrados:"]
    for match in matches:
        area = match.area or "Desconocido"
        artist_type = match.artist_type or "N/A"
        begin = match.begin_date or "?"
        end = match.end_date or "presente"
        tags = ", ".join(match.tags) if match.tags else "(sin tags)"
        genres = ", ".join(match.genres) if match.genres else "(sin géneros)"
        lines.append(
            f"- {match.artist_name} | Tipo: {artist_type} | Origen: {area} | "
            f"Período: {begin} - {end} | Álbumes: {match.album_count} | "
            f"Canciones: {match.song_count} | Géneros: {genres} | Tags: {tags}"
        )
    return "\n".join(lines)


# =============================================================================
# COLLABORATION SEARCH FUNCTIONS
# =============================================================================

def detect_collaboration_query(question: str) -> Tuple[bool, Optional[str]]:
    """
    Detect if the question is about collaborations.
    Returns: (is_collab_query, artist_term)
    """
    if not _has_keywords(question, _COLLAB_KEYWORDS):
        return False, None

    artist_term = _extract_quoted_term(question)
    if not artist_term:
        pattern = re.compile(
            r"(?:de|by|con|with|entre)\s+['\"]?([a-zA-Z0-9ÁÉÍÓÚÜÑáéíóúüñ\s\-]+)['\"]?",
            re.IGNORECASE,
        )
        match = pattern.search(question)
        if match:
            artist_term = _clean_term(match.group(1))

    return bool(artist_term), artist_term


def fetch_collaborations(artist_name: str, limit: int = 25) -> List[CollaborationMatch]:
    """Find collaborations involving an artist."""
    cypher = """
    MATCH (a1:Artist)-[:PERFORMED_ON]->(r:Recording)<-[:PERFORMED_ON]-(a2:Artist)
    WHERE toLower(a1.name) CONTAINS toLower($artist_name)
      AND a1 <> a2
    RETURN a1.name AS artist1_name,
           a2.name AS artist2_name,
           r.name AS recording_name,
           elementId(r) AS recording_id
    ORDER BY r.name
    LIMIT $limit
    """
    rows = query_graph(cypher, {"artist_name": artist_name, "limit": limit})

    matches: List[CollaborationMatch] = []
    for row in rows:
        if not row.get("recording_name"):
            continue
        matches.append(
            CollaborationMatch(
                artist1_name=row.get("artist1_name", ""),
                artist2_name=row.get("artist2_name", ""),
                recording_name=row.get("recording_name", ""),
                recording_id=row.get("recording_id", ""),
            )
        )
    return matches


def _format_collaboration_context(matches: List[CollaborationMatch], artist: str) -> str:
    lines = [f"Colaboraciones encontradas para '{artist}':"]
    for match in matches:
        lines.append(f"- {match.recording_name} | {match.artist1_name} con {match.artist2_name}")
    return "\n".join(lines)


# =============================================================================
# SIMILAR ARTISTS SEARCH
# =============================================================================

def detect_similar_query(question: str) -> Tuple[bool, Optional[str]]:
    """
    Detect if the question is asking for similar artists.
    Returns: (is_similar_query, artist_term)
    """
    if not _has_keywords(question, _SIMILAR_KEYWORDS):
        return False, None
    if not _has_keywords(question, _ARTIST_KEYWORDS):
        return False, None

    artist_term = _extract_quoted_term(question)
    if not artist_term:
        pattern = re.compile(
            r"(?:a|como|to|similar a)\s+['\"]?([a-zA-Z0-9ÁÉÍÓÚÜÑáéíóúüñ\s\-]+)['\"]?",
            re.IGNORECASE,
        )
        match = pattern.search(question)
        if match:
            artist_term = _clean_term(match.group(1))

    return bool(artist_term), artist_term


def fetch_similar_artists(artist_name: str, limit: int = 15) -> List[ArtistMatch]:
    """Find artists similar to the given one based on shared tags/genres."""
    cypher = """
    MATCH (a:Artist)-[:HAS_TAG]->(t)<-[:HAS_TAG]-(similar:Artist)
    WHERE toLower(a.name) CONTAINS toLower($artist_name)
      AND a <> similar
    WITH similar, count(t) AS shared_tags
    ORDER BY shared_tags DESC
    LIMIT $limit
    OPTIONAL MATCH (similar)-[:FROM_AREA]->(area:Area)
    OPTIONAL MATCH (similar)-[:HAS_TAG]->(st:Tag)
    OPTIONAL MATCH (similar)-[:HAS_TAG]->(sg:Genre)
    OPTIONAL MATCH (similar)-[:RELEASED]->(rel:Release)
    OPTIONAL MATCH (similar)-[:PERFORMED_ON]->(rec:Recording)
    WITH similar, area, shared_tags,
         collect(DISTINCT st.name) AS tags,
         collect(DISTINCT sg.name) AS genres,
         count(DISTINCT rel) AS album_count,
         count(DISTINCT rec) AS song_count
    RETURN elementId(similar) AS node_id,
           similar.name AS artist_name,
           area.name AS area,
           similar.begin_date AS begin_date,
           similar.end_date AS end_date,
           similar.type AS artist_type,
           [t IN tags WHERE t IS NOT NULL | t] AS tags,
           [g IN genres WHERE g IS NOT NULL | g] AS genres,
           album_count,
           song_count,
           shared_tags
    ORDER BY shared_tags DESC
    """
    rows = query_graph(cypher, {"artist_name": artist_name, "limit": limit})

    matches: List[ArtistMatch] = []
    for row in rows:
        node_id = row.get("node_id")
        name = row.get("artist_name")
        if not node_id or not name:
            continue
        matches.append(
            ArtistMatch(
                node_id=node_id,
                artist_name=name,
                area=row.get("area"),
                begin_date=row.get("begin_date"),
                end_date=row.get("end_date"),
                artist_type=row.get("artist_type"),
                tags=sorted({t for t in (row.get("tags") or []) if t}),
                genres=sorted({g for g in (row.get("genres") or []) if g}),
                album_count=row.get("album_count", 0),
                song_count=row.get("song_count", 0),
            )
        )
    return matches


def _format_similar_artists_context(matches: List[ArtistMatch], original: str) -> str:
    lines = [f"Artistas similares a '{original}' (basado en tags/géneros compartidos):"]
    for match in matches:
        genres = ", ".join(match.genres) if match.genres else "(sin géneros)"
        tags = ", ".join(match.tags[:5]) if match.tags else "(sin tags)"
        lines.append(f"- {match.artist_name} | Géneros: {genres} | Tags: {tags}")
    return "\n".join(lines)


# =============================================================================
# ARTISTS BY AREA/LOCATION
# =============================================================================

def detect_area_query(question: str) -> Tuple[bool, Optional[str]]:
    """
    Detect if the question is about artists from a specific area.
    Returns: (is_area_query, area_term)
    """
    if not _has_keywords(question, _AREA_KEYWORDS):
        return False, None
    if not _has_keywords(question, _ARTIST_KEYWORDS):
        return False, None

    area_term = _extract_quoted_term(question)
    if not area_term:
        pattern = re.compile(
            r"(?:de|from|en|in|del?)\s+['\"]?([a-zA-Z0-9ÁÉÍÓÚÜÑáéíóúüñ\s\-]+)['\"]?",
            re.IGNORECASE,
        )
        match = pattern.search(question)
        if match:
            area_term = _clean_term(match.group(1))

    return bool(area_term), area_term


def fetch_artists_by_area(area_name: str, limit: int = 25) -> List[ArtistMatch]:
    """Find artists from a specific area/country."""
    cypher = """
    MATCH (a:Artist)-[:FROM_AREA]->(area:Area)
    WHERE toLower(area.name) CONTAINS toLower($area_name)
    OPTIONAL MATCH (a)-[:HAS_TAG]->(t:Tag)
    OPTIONAL MATCH (a)-[:HAS_TAG]->(g:Genre)
    OPTIONAL MATCH (a)-[:RELEASED]->(rel:Release)
    OPTIONAL MATCH (a)-[:PERFORMED_ON]->(rec:Recording)
    WITH a, area,
         collect(DISTINCT t.name) AS tags,
         collect(DISTINCT g.name) AS genres,
         count(DISTINCT rel) AS album_count,
         count(DISTINCT rec) AS song_count
    RETURN elementId(a) AS node_id,
           a.name AS artist_name,
           area.name AS area,
           a.begin_date AS begin_date,
           a.end_date AS end_date,
           a.type AS artist_type,
           [t IN tags WHERE t IS NOT NULL | t] AS tags,
           [g IN genres WHERE g IS NOT NULL | g] AS genres,
           album_count,
           song_count
    ORDER BY song_count DESC
    LIMIT $limit
    """
    rows = query_graph(cypher, {"area_name": area_name, "limit": limit})

    matches: List[ArtistMatch] = []
    for row in rows:
        node_id = row.get("node_id")
        name = row.get("artist_name")
        if not node_id or not name:
            continue
        matches.append(
            ArtistMatch(
                node_id=node_id,
                artist_name=name,
                area=row.get("area"),
                begin_date=row.get("begin_date"),
                end_date=row.get("end_date"),
                artist_type=row.get("artist_type"),
                tags=sorted({t for t in (row.get("tags") or []) if t}),
                genres=sorted({g for g in (row.get("genres") or []) if g}),
                album_count=row.get("album_count", 0),
                song_count=row.get("song_count", 0),
            )
        )
    return matches


def _format_area_artists_context(matches: List[ArtistMatch], area: str) -> str:
    lines = [f"Artistas de '{area}':"]
    for match in matches:
        genres = ", ".join(match.genres) if match.genres else "(sin géneros)"
        lines.append(f"- {match.artist_name} | Tipo: {match.artist_type or 'N/A'} | Géneros: {genres} | Canciones: {match.song_count}")
    return "\n".join(lines)


# =============================================================================
# POPULAR/TOP QUERIES
# =============================================================================

def detect_popular_query(question: str) -> Tuple[bool, Optional[str]]:
    """
    Detect if the question is asking for popular items.
    Returns: (is_popular_query, category - 'artist', 'song', or 'album')
    """
    if not _has_keywords(question, _POPULAR_KEYWORDS):
        return False, None

    if _has_keywords(question, _SONG_KEYWORDS):
        return True, "song"
    if _has_keywords(question, _ALBUM_KEYWORDS):
        return True, "album"
    if _has_keywords(question, _ARTIST_KEYWORDS):
        return True, "artist"

    return True, "artist"  # Default to artists


def fetch_popular_artists(limit: int = 20) -> List[ArtistMatch]:
    """Get artists with the most recordings/releases."""
    cypher = """
    MATCH (a:Artist)
    OPTIONAL MATCH (a)-[:PERFORMED_ON]->(rec:Recording)
    OPTIONAL MATCH (a)-[:RELEASED]->(rel:Release)
    OPTIONAL MATCH (a)-[:FROM_AREA]->(area:Area)
    OPTIONAL MATCH (a)-[:HAS_TAG]->(t:Tag)
    OPTIONAL MATCH (a)-[:HAS_TAG]->(g:Genre)
    WITH a, area,
         count(DISTINCT rec) AS song_count,
         count(DISTINCT rel) AS album_count,
         collect(DISTINCT t.name) AS tags,
         collect(DISTINCT g.name) AS genres
    WHERE song_count > 0
    RETURN elementId(a) AS node_id,
           a.name AS artist_name,
           area.name AS area,
           a.begin_date AS begin_date,
           a.end_date AS end_date,
           a.type AS artist_type,
           [t IN tags WHERE t IS NOT NULL | t] AS tags,
           [g IN genres WHERE g IS NOT NULL | g] AS genres,
           album_count,
           song_count
    ORDER BY song_count DESC, album_count DESC
    LIMIT $limit
    """
    rows = query_graph(cypher, {"limit": limit})

    matches: List[ArtistMatch] = []
    for row in rows:
        node_id = row.get("node_id")
        name = row.get("artist_name")
        if not node_id or not name:
            continue
        matches.append(
            ArtistMatch(
                node_id=node_id,
                artist_name=name,
                area=row.get("area"),
                begin_date=row.get("begin_date"),
                end_date=row.get("end_date"),
                artist_type=row.get("artist_type"),
                tags=sorted({t for t in (row.get("tags") or []) if t}),
                genres=sorted({g for g in (row.get("genres") or []) if g}),
                album_count=row.get("album_count", 0),
                song_count=row.get("song_count", 0),
            )
        )
    return matches


def _format_popular_context(matches: List[ArtistMatch]) -> str:
    lines = ["Artistas más populares (por número de canciones):"]
    for i, match in enumerate(matches, 1):
        genres = ", ".join(match.genres[:3]) if match.genres else "(sin géneros)"
        lines.append(f"{i}. {match.artist_name} | Canciones: {match.song_count} | Álbumes: {match.album_count} | Géneros: {genres}")
    return "\n".join(lines)


def run_semantic_query(
    question: str, top_k: int = 8, include_debug: bool = False
) -> QueryEngineResult:
    """
    Execute a semantic query with intelligent detection of query type.
    
    Supports:
    - Tag/genre searches for artists
    - Song/recording searches by name or artist
    - Album/release searches by name or artist
    - Artist detail queries
    - Collaboration queries
    - Similar artist queries
    - Area/location-based artist queries
    - Popular/top queries
    """
    top_k = max(1, min(top_k, 20))

    context_sections: List[str] = []
    query_type = "general"
    
    # Result containers
    tag_term: Optional[str] = None
    tag_matches: List[ArtistTagMatch] = []
    song_matches: List[SongMatch] = []
    album_matches: List[AlbumMatch] = []
    artist_matches: List[ArtistMatch] = []
    collaboration_matches: List[CollaborationMatch] = []

    # 1. Check for songs by genre/tag queries (highest priority for combined queries)
    # This handles "canciones de artistas de jazz", "mejores canciones de rock", etc.
    is_songs_by_genre, genre_for_songs = detect_songs_by_genre_query(question)
    if is_songs_by_genre and genre_for_songs:
        query_type = "songs_by_genre"
        song_matches = fetch_songs_by_genre(genre_for_songs)
        if song_matches:
            context_sections.append(_format_songs_by_genre_context(song_matches, genre_for_songs))
        # Also get the artists for this genre for additional context
        tag_term = genre_for_songs
        tag_matches = fetch_artists_by_tag(genre_for_songs)
        if tag_matches:
            context_sections.append(_format_artist_tag_context(genre_for_songs, tag_matches))

    # 2. Check for song/recording queries
    is_song_query, song_term, song_artist = detect_song_query(question)
    if is_song_query and query_type == "general":
        query_type = "song"
        if song_artist:
            song_matches = fetch_songs_by_artist(song_artist)
            if song_matches:
                context_sections.append(_format_song_context(song_matches, f"artista '{song_artist}'"))
        elif song_term:
            song_matches = fetch_songs_by_name(song_term)
            if song_matches:
                context_sections.append(_format_song_context(song_matches, f"nombre '{song_term}'"))

    # 2. Check for album queries
    is_album_query, album_term, album_artist = detect_album_query(question)
    if is_album_query:
        query_type = "album"
        if album_artist:
            album_matches = fetch_albums_by_artist(album_artist)
            if album_matches:
                context_sections.append(_format_album_context(album_matches, f"artista '{album_artist}'"))
        elif album_term:
            album_matches = fetch_albums_by_name(album_term)
            if album_matches:
                context_sections.append(_format_album_context(album_matches, f"nombre '{album_term}'"))

    # 3. Check for collaboration queries
    is_collab_query, collab_artist = detect_collaboration_query(question)
    if is_collab_query and collab_artist:
        query_type = "collaboration"
        collaboration_matches = fetch_collaborations(collab_artist)
        if collaboration_matches:
            context_sections.append(_format_collaboration_context(collaboration_matches, collab_artist))

    # 4. Check for similar artist queries
    is_similar_query, similar_artist = detect_similar_query(question)
    if is_similar_query and similar_artist:
        query_type = "similar"
        artist_matches = fetch_similar_artists(similar_artist)
        if artist_matches:
            context_sections.append(_format_similar_artists_context(artist_matches, similar_artist))

    # 5. Check for area-based queries
    is_area_query, area_term = detect_area_query(question)
    if is_area_query and area_term:
        query_type = "area"
        artist_matches = fetch_artists_by_area(area_term)
        if artist_matches:
            context_sections.append(_format_area_artists_context(artist_matches, area_term))

    # 6. Check for popular/top queries
    is_popular_query, popular_category = detect_popular_query(question)
    if is_popular_query and query_type == "general":
        query_type = "popular"
        if popular_category == "artist":
            artist_matches = fetch_popular_artists()
            if artist_matches:
                context_sections.append(_format_popular_context(artist_matches))

    # 7. Check for artist detail queries
    is_artist_query, artist_term = detect_artist_detail_query(question)
    if is_artist_query and artist_term and query_type == "general":
        query_type = "artist_detail"
        artist_matches = fetch_artist_details(artist_term)
        if artist_matches:
            context_sections.append(_format_artist_detail_context(artist_matches))

    # 8. Check for tag/genre queries (original functionality)
    tag_term = detect_artist_tag_term(question)
    if tag_term and query_type == "general":
        query_type = "tag"
        tag_matches = fetch_artists_by_tag(tag_term)
        if tag_matches:
            context_sections.append(_format_artist_tag_context(tag_term, tag_matches))

    # 9. Always add vector/graph context for enrichment
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
        query_type=query_type,
        tag_term=tag_term,
        tag_matches=tag_matches,
        song_matches=song_matches,
        album_matches=album_matches,
        artist_matches=artist_matches,
        collaboration_matches=collaboration_matches,
        debug=debug_info,
    )
