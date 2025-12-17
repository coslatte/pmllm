import json
import os
import sys
from typing import Any, Dict, List

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.neo4j.neo4j_handler import query_graph
from db.vector.rag_pipeline import build_context, llm_generate


def generate_recommendations_for_user(
    user_profile_text: str, user_preferences: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generates music recommendations based on user profile and preferences using RAG.
    """

    # 1. Retrieve context from Vector DB (Milvus) and Graph DB (Neo4j)
    # We use the profile text as the query to find semantically similar items
    context_docs = build_context(user_profile_text, top_k=10)
    context_str = "\n".join(context_docs)

    # 2. Construct the prompt
    # Adapted from the user's request to fit the Music domain
    system_prompt = f"""
You are an intelligent assistant specialized in personalized music recommendations. Your role is to generate recommendations for artists, albums, and tracks based on a knowledge graph (Neo4j) and semantic similarities (Milvus). Use the provided information about the user's profile and the retrieved context to make relevant, explainable, and reliable recommendations.

**CRITICAL INSTRUCTION**: You MUST respond in the SAME language as the user's profile text.
- If the user profile is in Spanish, respond entirely in Spanish (including all fields in the JSON).
- If the user profile is in English, respond entirely in English.
- Match the user's language exactly.

Key Instructions:
- **Personalization**: Tailor recommendations to the user's profile (e.g., favorite genres: {", ".join(user_preferences.get("fav_genres", []))}, artists: {", ".join(user_preferences.get("fav_artists", []))}, instruments: {", ".join(user_preferences.get("fav_instruments", []))}).
- **Output Structure**: Always respond in valid JSON format with the following structure:
  {{
    "recommendations": [
      {{
        "type": "artist|album|track",
        "title": "Name of the artist, album, or track",
        "description": "Short description",
        "explanation": "Detailed explanation of why it is recommended, based on semantic similarities or graph relationships. Include logical connections.",
        "confidence": 0.0 to 1.0,
        "sources": ["source1", "source2"],
        "suggested_actions": ["Listen to...", "Explore discography"]
      }}
    ],
    "general_summary": "Brief summary of the recommendations, highlighting common patterns or themes."
  }}
- **Quality Criteria**: Prioritize recommendations with high confidence (>=0.7). If there is insufficient data, state 'Insufficient recommendations available'. Include at least 5 recommendations.
- **System Metaphor**: Think of Neo4j as the 'logical brain' (exact relationships) and Milvus as the 'intuitive brain' (semantic similarities).

Provided Context:
- User Profile Text: {user_profile_text}
- Retrieved Knowledge (RAG Context):
{context_str}

Generate the recommendations now in JSON format.
"""

    # 3. Call LLM
    response_text = llm_generate(system_prompt)

    # 4. Parse JSON response
    try:
        # Clean up potential markdown code blocks
        cleaned_response = response_text.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]

        return json.loads(cleaned_response)
    except json.JSONDecodeError:
        # Fallback if LLM didn't return valid JSON
        return {
            "recommendations": [],
            "general_summary": "Error parsing recommendations. Raw response: "
            + response_text[:100]
            + "...",
            "raw_response": response_text,
        }


def _normalize_genres(values: List[str]) -> List[str]:
    return sorted({value.strip().lower() for value in values if value and value.strip()})


def recommend_albums_by_preferences(
    include_genres: List[str],
    exclude_genres: List[str] | None = None,
    include_artists: List[str] | None = None,
    exclude_artists: List[str] | None = None,
    include_tags: List[str] | None = None,
    exclude_tags: List[str] | None = None,
    *,
    limit: int = 12,
    min_overlap: int = 1,
) -> List[Dict[str, Any]]:
    """Return albums (releases) that align with the provided user preferences.
    
    This function uses a multi-strategy approach:
    1. First tries to find releases via graph relationships (HAS_TAG, RELEASED)
    2. Falls back to searching artists by name and finding their works
    3. As a last resort, uses text-based search on release names
    
    If no preferences are provided, returns discovery recommendations.
    This ensures results even when the graph has sparse relationships.
    """
    include_g = _normalize_genres(include_genres)
    exclude_g = _normalize_genres(exclude_genres or [])
    include_a = _normalize_genres(include_artists or [])
    exclude_a = _normalize_genres(exclude_artists or [])
    include_t = _normalize_genres(include_tags or [])
    exclude_t = _normalize_genres(exclude_tags or [])

    safe_limit = max(1, min(limit, 50))
    all_include_tags = list(set(include_g + include_t))
    all_exclude_tags = list(set(exclude_g + exclude_t))
    
    recommendations: List[Dict[str, Any]] = []
    
    # If no preferences at all, go straight to discovery mode
    discovery_mode = not include_g and not include_a and not include_t
    
    if discovery_mode:
        # Discovery mode: return interesting releases to explore
        existing_ids: set = set()
        fallback_results = _get_fallback_releases([], [], safe_limit, existing_ids)
        recommendations.extend(fallback_results)
        recommendations.sort(key=lambda x: x.get("score", 0), reverse=True)
        return recommendations[:safe_limit]
    
    # Strategy 1: Search by artist name (most common case for users)
    if include_a:
        artist_results = _search_releases_by_artist_name(include_a, exclude_a, safe_limit)
        recommendations.extend(artist_results)
    
    # Strategy 2: Search by tags/genres via graph relationships  
    if all_include_tags and len(recommendations) < safe_limit:
        remaining = safe_limit - len(recommendations)
        existing_ids = {r["release_id"] for r in recommendations}
        tag_results = _search_releases_by_tags(all_include_tags, all_exclude_tags, remaining, existing_ids)
        recommendations.extend(tag_results)
    
    # Strategy 3: Fallback - get releases with any connected data
    if len(recommendations) < safe_limit:
        remaining = safe_limit - len(recommendations)
        existing_ids = {r["release_id"] for r in recommendations}
        fallback_results = _get_fallback_releases(include_g, include_a, remaining, existing_ids)
        recommendations.extend(fallback_results)
    
    # Sort by score descending
    recommendations.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    return recommendations[:safe_limit]


def _search_releases_by_artist_name(
    include_artists: List[str], 
    exclude_artists: List[str],
    limit: int
) -> List[Dict[str, Any]]:
    """Search for releases by artist name using fuzzy matching."""
    
    # Build regex pattern for artist matching
    artist_patterns = [f"(?i).*{a}.*" for a in include_artists]
    
    cypher = """
    // Find artists matching the search terms
    MATCH (artist:Artist)
    WHERE any(pattern IN $artist_patterns WHERE artist.name =~ pattern)
    
    // Get releases by these artists (via relationship or referenced in release)
    OPTIONAL MATCH (artist)-[:RELEASED]->(release:Release)
    WITH artist, collect(DISTINCT release) AS direct_releases
    
    // Also find releases that might reference this artist in their name
    OPTIONAL MATCH (release2:Release)
    WHERE release2.name =~ ('(?i).*' + artist.name + '.*')
    
    WITH artist, direct_releases, collect(DISTINCT release2) AS name_matched_releases
    
    // Combine all releases
    WITH artist, direct_releases + name_matched_releases AS all_releases
    UNWIND all_releases AS release
    
    WITH DISTINCT release, collect(DISTINCT artist.name) AS matched_artist_names
    WHERE release IS NOT NULL
    
    // Get additional info
    OPTIONAL MATCH (release)-[:BELONGS_TO]-(rg:ReleaseGroup)
    OPTIONAL MATCH (release)-[:HAS_TAG]->(tag:Tag)
    
    RETURN 
        elementId(release) AS release_id,
        release.name AS release_name,
        coalesce(rg.name, release.name) AS release_group_name,
        matched_artist_names AS artists,
        matched_artist_names AS matched_artists,
        collect(DISTINCT tag.name) AS tags,
        collect(DISTINCT tag.name) AS all_genres,
        [] AS matched_genres,
        [] AS matched_tags,
        0 AS genre_match_count,
        size(matched_artist_names) AS artist_match_count,
        0 AS tag_match_count,
        size(matched_artist_names) * 5.0 AS relevance_score
    ORDER BY relevance_score DESC, release_name ASC
    LIMIT $limit
    """
    
    params = {
        "artist_patterns": artist_patterns,
        "limit": limit,
    }
    
    rows = query_graph(cypher, params)
    return _process_recommendation_rows(rows, include_artists, [])


def _search_releases_by_tags(
    include_tags: List[str],
    exclude_tags: List[str], 
    limit: int,
    exclude_ids: set
) -> List[Dict[str, Any]]:
    """Search for releases by tags/genres."""
    
    cypher = """
    MATCH (release:Release)-[:HAS_TAG]->(tag:Tag)
    WHERE toLower(tag.name) IN $include_tags
      AND NOT elementId(release) IN $exclude_ids
    
    WITH release, collect(DISTINCT tag.name) AS matched_tags
    
    OPTIONAL MATCH (release)<-[:RELEASED]-(artist:Artist)
    OPTIONAL MATCH (release)-[:BELONGS_TO]-(rg:ReleaseGroup)
    OPTIONAL MATCH (release)-[:HAS_TAG]->(all_tag:Tag)
    
    RETURN 
        elementId(release) AS release_id,
        release.name AS release_name,
        coalesce(rg.name, release.name) AS release_group_name,
        collect(DISTINCT artist.name) AS artists,
        [] AS matched_artists,
        collect(DISTINCT all_tag.name) AS tags,
        collect(DISTINCT all_tag.name) AS all_genres,
        matched_tags AS matched_genres,
        matched_tags AS matched_tags,
        size(matched_tags) AS genre_match_count,
        0 AS artist_match_count,
        size(matched_tags) AS tag_match_count,
        size(matched_tags) * 3.0 AS relevance_score
    ORDER BY relevance_score DESC, release_name ASC
    LIMIT $limit
    """
    
    params = {
        "include_tags": include_tags,
        "exclude_ids": list(exclude_ids),
        "limit": limit,
    }
    
    rows = query_graph(cypher, params)
    return _process_recommendation_rows(rows, [], include_tags)


def _get_fallback_releases(
    include_genres: List[str],
    include_artists: List[str],
    limit: int,
    exclude_ids: set
) -> List[Dict[str, Any]]:
    """Get random releases with some artist data as fallback."""
    
    cypher = """
    // Get releases with artists connected (better quality data)
    MATCH (release:Release)
    WHERE NOT elementId(release) IN $exclude_ids
    
    OPTIONAL MATCH (release)<-[:RELEASED]-(artist:Artist)
    OPTIONAL MATCH (release)-[:BELONGS_TO]-(rg:ReleaseGroup)
    OPTIONAL MATCH (release)-[:HAS_TAG]->(tag:Tag)
    
    WITH release, rg,
         collect(DISTINCT artist.name) AS artist_names,
         collect(DISTINCT tag.name) AS tag_names
    
    // Prefer releases with some metadata
    WITH release, rg, artist_names, tag_names,
         CASE 
           WHEN size(artist_names) > 0 THEN 1.0
           WHEN size(tag_names) > 0 THEN 0.5
           ELSE 0.1
         END AS base_score
    
    RETURN 
        elementId(release) AS release_id,
        release.name AS release_name,
        coalesce(rg.name, release.name) AS release_group_name,
        artist_names AS artists,
        [] AS matched_artists,
        tag_names AS tags,
        tag_names AS all_genres,
        [] AS matched_genres,
        [] AS matched_tags,
        0 AS genre_match_count,
        0 AS artist_match_count,
        0 AS tag_match_count,
        base_score AS relevance_score
    ORDER BY base_score DESC, rand()
    LIMIT $limit
    """
    
    params = {
        "exclude_ids": list(exclude_ids),
        "limit": limit,
    }
    
    rows = query_graph(cypher, params)
    return _process_recommendation_rows(rows, include_artists, include_genres, is_fallback=True)


def _process_recommendation_rows(
    rows: List[Dict[str, Any]], 
    include_artists: List[str],
    include_tags: List[str],
    is_fallback: bool = False
) -> List[Dict[str, Any]]:
    """Process Neo4j result rows into recommendation format."""
    recommendations: List[Dict[str, Any]] = []
    
    for row in rows:
        release_id = row.get("release_id")
        release_name = row.get("release_name")
        if not release_id or not release_name:
            continue

        matched_genres = row.get("matched_genres") or []
        matched_artists = row.get("matched_artists") or []
        matched_tags = row.get("matched_tags") or []
        artists = row.get("artists") or []
        
        # Filter out None values from artists
        artists = [a for a in artists if a]
        matched_artists = [a for a in matched_artists if a]
        
        # Build explanation
        reasons: List[str] = []
        if matched_artists:
            reasons.append(f"Artista: {', '.join(matched_artists[:2])}")
        elif artists and include_artists:
            # Check if any artist name partially matches
            for artist in artists:
                if artist and any(inc.lower() in artist.lower() for inc in include_artists):
                    reasons.append(f"Artista similar: {artist}")
                    break
        if matched_genres:
            reasons.append(f"Género: {', '.join(matched_genres[:3])}")
        if matched_tags and matched_tags != matched_genres:
            reasons.append(f"Tags: {', '.join(matched_tags[:3])}")
        if is_fallback and not reasons:
            if artists:
                reasons.append(f"Por {', '.join(artists[:2])}")
            else:
                reasons.append("Descubrimiento musical")

        recommendations.append({
            "release_id": release_id,
            "release_name": release_name,
            "release_group_name": row.get("release_group_name"),
            "artists": artists,
            "matched_artists": matched_artists,
            "all_genres": row.get("all_genres") or [],
            "matched_genres": matched_genres,
            "tags": row.get("tags") or [],
            "matched_tags": matched_tags,
            "genre_match_count": int(row.get("genre_match_count") or 0),
            "artist_match_count": int(row.get("artist_match_count") or 0),
            "tag_match_count": int(row.get("tag_match_count") or 0),
            "score": float(row.get("relevance_score") or 0.0),
            "match_reasons": reasons,
        })

    return recommendations


def recommend_albums_by_genres(
    include_genres: List[str],
    exclude_genres: List[str] | None = None,
    *,
    limit: int = 12,
    min_overlap: int = 1,
) -> List[Dict[str, Any]]:
    """Return albums (releases) that align with the provided genre filters."""

    include = _normalize_genres(include_genres)
    exclude = _normalize_genres(exclude_genres or [])


    if not include:
        raise ValueError("At least one include_genre is required to compute album recommendations.")

    safe_limit = max(1, min(limit, 50))
    safe_overlap = max(1, min(min_overlap, len(include)))

    # Note: In this database, genres are stored as Tags with HAS_TAG relationship
    cypher = """
    MATCH (release:Release)-[:HAS_TAG]-(tag:Tag)
    WHERE (size($include) = 0 OR toLower(tag.name) IN $include)
      AND (size($exclude) = 0 OR NOT EXISTS {
        MATCH (release)-[:HAS_TAG]-(bad:Tag)
        WHERE toLower(bad.name) IN $exclude
        })
    WITH release,
       collect(DISTINCT tag) AS liked_nodes,
       collect(DISTINCT {name: tag.name, rel: 'HAS_TAG'}) AS tag_links
    WHERE size(liked_nodes) >= CASE WHEN size($include) = 0 THEN 1 ELSE $min_overlap END
    OPTIONAL MATCH (release)-[:BELONGS_TO]-(rg:ReleaseGroup)
    OPTIONAL MATCH (release)<-[:RELEASED]-(artist:Artist)
        WITH release,
          rg,
          liked_nodes,
          tag_links,
          [name IN collect(DISTINCT artist.name) WHERE name IS NOT NULL | name] AS artist_names
    RETURN elementId(release) AS release_id,
         release.name AS release_name,
         coalesce(rg.name, release.name) AS release_group_name,
         [t IN liked_nodes | t.name] AS matched_genres,
         tag_links AS genre_links,
         artist_names AS artists,
         [t IN liked_nodes | t.name] AS tags,
         size(liked_nodes) AS matched_count,
         size(artist_names) AS artist_count,
         size(liked_nodes) AS tag_count,
         (size(liked_nodes) * 1.0) + (size(artist_names) * 0.2) AS relevance_score
    ORDER BY relevance_score DESC, release_name ASC
    LIMIT $limit
    """

    params = {
      "include": include,
      "exclude": exclude,
      "limit": safe_limit,
      "min_overlap": safe_overlap,
    }

    rows = query_graph(cypher, params)
    recommendations: List[Dict[str, Any]] = []
    for row in rows:
      release_id = row.get("release_id")
      release_name = row.get("release_name")
      if not release_id or not release_name:
        continue

      connections: List[str] = []
      for link in row.get("genre_links") or []:
        name = link.get("name") if isinstance(link, dict) else None
        rel = link.get("rel") if isinstance(link, dict) else None
        if name:
          label = rel or "RELATED"
          connections.append(f"{label}:{name}")

      recommendations.append(
        {
          "release_id": release_id,
          "release_name": release_name,
          "release_group_name": row.get("release_group_name"),
          "matched_genres": row.get("matched_genres") or [],
          "artists": row.get("artists") or [],
          "tags": row.get("tags") or [],
          "connections": connections,
          "score": float(row.get("relevance_score") or 0.0),
          "matched_count": int(row.get("matched_count") or 0),
        }
      )

    return recommendations

