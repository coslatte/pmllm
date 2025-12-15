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

    cypher = """
    MATCH (release:Release)-[genre_rel]-(genre:Genre)
    WHERE (size($include) = 0 OR toLower(genre.name) IN $include)
      AND (size($exclude) = 0 OR NOT EXISTS {
        MATCH (release)-[bad_rel]-(bad:Genre)
        WHERE toLower(bad.name) IN $exclude
        })
    WITH release,
       collect(DISTINCT genre) AS liked_nodes,
       collect(DISTINCT {name: genre.name, rel: type(genre_rel)}) AS genre_links
    WHERE size(liked_nodes) >= CASE WHEN size($include) = 0 THEN 1 ELSE $min_overlap END
    OPTIONAL MATCH (release)-[rg_rel]-(rg:ReleaseGroup)
    OPTIONAL MATCH (release)<-[artist_rel]-(artist:Artist)
    OPTIONAL MATCH (release)-[tag_rel]-(tag:Tag)
        WITH release,
          rg,
          liked_nodes,
          genre_links,
          [name IN collect(DISTINCT artist.name) WHERE name IS NOT NULL | name] AS artist_names,
          [name IN collect(DISTINCT tag.name) WHERE name IS NOT NULL | name] AS tag_names
    RETURN elementId(release) AS release_id,
         release.name AS release_name,
         coalesce(rg.name, release.name) AS release_group_name,
         [g IN liked_nodes | g.name] AS matched_genres,
         genre_links,
         artist_names AS artists,
         tag_names AS tags,
         size(liked_nodes) AS matched_count,
         size(artist_names) AS artist_count,
         size(tag_names) AS tag_count,
         (size(liked_nodes) * 1.0) + (size(artist_names) * 0.2) + (size(tag_names) * 0.1) AS relevance_score
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
