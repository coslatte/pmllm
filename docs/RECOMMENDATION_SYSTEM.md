# Recommendation System Specification

This document defines how the personalized recommendation agent should operate when combining Neo4j ("logical brain") and Milvus ("intuitive brain") signals with the Gemma 3 LLM. It codifies the JSON output contract, required inputs, and the album-plan experience requested for the music domain.

## 1. Purpose

- Provide explainable recommendations for university students and professionals by mixing graph relationships and vector similarities.
- Extend the existing course/content/connection contracts to surface **album listening plans** derived from a user's stated tastes (e.g., favorite artists or genres).

## 2. Required Inputs

Each invocation must supply the following contextual blobs (typically fetched from the orchestrator):

- `user_profile`: static facts such as role, academic program, or favorite artists.
- `user_preferences`: dynamic tastes ("prefers progressive rock", "loves concept albums").
- `history`: prior interactions (viewed items, skipped suggestions, saved albums).
- `current_query`: the explicit request ("Recommend albums like Queen's catalog").
- `graph_context`: list of Neo4j nodes/relationships already retrieved (artist → release, release_group → tag, etc.).
- `vector_hits`: Milvus matches with similarity scores for semantically close content.

## 3. Prompt Skeleton

```text
You are an intelligent assistant specialized in personalized recommendations for university students and professionals. Your role is to generate recommendations for courses, educational content, professional connections, and music albums based on a knowledge graph (Neo4j) and semantic similarities (Milvus).

<Context>
- User Profile: {user_profile}
- Preferences: {user_preferences}
- History: {user_history}
- Query: {current_query}
- Graph Context: {graph_context}
- Vector Matches: {vector_hits}
</Context>

Instructions:
1. Personalize recommendations to the profile + history.
2. Combine logical relationships (Neo4j) with semantic cues (Milvus).
3. When the query references music tastes, assemble a multi-step **album listening plan**. Each step can cite an album, release group, or curated playlist derived from similar artists.
4. Output valid JSON exactly matching the schema described below.
5. Prefer confidence ≥ 0.7. If not possible, return "Insufficient recommendations available" and advise collecting more data.
```

## 4. JSON Output Contract

```json
{
  "recommendations": [
    {
      "type": "course | content | connection | album_plan",
      "title": "Short descriptive name",
      "description": "One-sentence summary of the item or album step",
      "explanation": "Traceable reasoning that cites graph nodes or vector hits (e.g., 'Shares release_group tags with Queen and appears in Milvus neighbors for glam rock').",
      "confidence": 0.0,
      "sources": ["neo4j:Artist(Queen)", "milvus:vector_id_123"],
      "suggested_actions": ["Listen on platform", "Connect with curator"]
    }
  ],
  "general_summary": "Highlight overlap among the recommendations or ask for clarification if the query was ambiguous."
}
```

- Always return **5–10 entries** when data suffices. Mix types if the user profile spans courses/content/connections alongside album plans.
- For album plans, treat each recommendation as a sequenced step (e.g., "Step 1 – Revisit Queen live anthologies"), but keep the schema identical by labeling `type: "album_plan"` and embedding the step order inside `title` or `description`.

## 5. Album Plan Assembly

1. **Seed Selection**: Start from the user's favorite artist nodes (e.g., Queen) via `MATCH (a:Artist {name})-[:PERFORMED_ON]->(r:Recording)`.
2. **Graph Expansion**: Traverse related release groups, genres, or collaboration hubs to find adjacent albums.
3. **Semantic Boosting**: Query Milvus for embeddings similar to the user's history or the seed artist to catch stylistically close but graph-distant options.
4. **Curation Logic**:
   - Step ordering should show narrative flow (e.g., "Foundational classics" → "Experimental era" → "Modern tributes").
   - Each step must cite at least one graph fact (shared genre tag, common collaborator) _and_ optionally a similarity score ("cosine 0.83 to 'A Night at the Opera'").

## 6. Confidence & Provenance

- Score confidence by blending Milvus cosine similarity (scaled to 0–1) with rule-based boosts for direct Neo4j hops.
- `sources` should explicitly name the contributing entities (e.g., `neo4j:ReleaseGroup(OperaRockSaga)` or `milvus:rec_9876`).

## 7. Failure Handling

- If fewer than three reliable items are available, respond with `"recommendations": []` and set `"general_summary": "Insufficient recommendations available. Collect more preferences."`
- Never invent albums or courses; rely solely on retrieved context.

## 8. Implementation Notes

- Keep prompts deterministic when possible (set temperature via caller; default 0.2 in Gemma 3 config).
- Respect the existing contracts outlined in `plan/PLAN.md` (content recommender, connector, QA responder). Album plans extend the **content recommender** contract.
- All orchestration code should load this spec to validate outputs before returning them to end users.

## 9. Quality Criteria & Guardrails

- **Personalization mandate**: Always ground each recommendation in the provided `user_profile`, `user_preferences`, and `history`. If those blobs are empty, surface that limitation in the summary.
- **Confidence floor**: Favor items scoring ≥ 0.7; when nothing meets the bar, emit `"Insufficient recommendations available"` plus a request for more data.
- **Coverage rules**: Return 5–10 entries whenever adequate data exists and mix recommendation types when the query spans multiple intents.
- **Ambiguity handling**: If the query is vague, explicitly ask for clarification inside `general_summary` instead of hallucinating.

## 10. Database-Driven Album Recommendations (Updated 2025-12-17)

The `recommend_albums_by_preferences()` function in `server/recommendation_engine.py` implements a multi-strategy approach for finding relevant albums when the knowledge graph has sparse relationship data.

### 10.1 Strategy Overview

The system uses a three-tier fallback strategy:

1. **Strategy 1: Artist Name Search** (Highest Priority)
   - Regex matching on Artist.name
   - Finds releases via RELEASED relationship OR name matching
   - Score: 5.0 per matched artist

2. **Strategy 2: Tag/Genre Search**
   - Direct HAS_TAG relationship traversal
   - Excludes already-found releases
   - Score: 3.0 per matched tag

3. **Strategy 3: Intelligent Fallback**
   - Returns releases with any connected metadata
   - Prioritizes releases with artists/tags
   - Score: 0.1 - 1.0 (discovery mode)

### 10.2 Scoring System

| Match Type           | Score  | Example                                    |
|---------------------|--------|---------------------------------------------|
| Exact artist match  | 5.0    | Search "Erik Satie" -> "Piano Works"        |
| Tag/genre match     | 3.0    | Search "rock" -> Albums with rock tag       |
| Fallback with artist| 1.0    | Album has artist data but no match         |
| Fallback with tags  | 0.5    | Album has tags but no match                |
| Pure discovery      | 0.1    | Random album for exploration               |

### 10.3 Match Reasons

Each recommendation includes human-readable `match_reasons` in Spanish:

- `"Artista: Erik Satie"` - Direct artist match
- `"Artista similar: Name"` - Partial name match
- `"Genero: rock, jazz"` - Tag/genre matches
- `"Por Artist1, Artist2"` - Fallback with known artists
- `"Descubrimiento musical"` - Pure discovery item

### 10.4 Handling Sparse Data

The system is designed to work even when:
- Most releases lack HAS_TAG relationships
- Few RELEASED relationships exist between artists and releases
- The graph was imported with minimal sampling

In these cases, the fallback strategy ensures users always receive recommendations, labeled appropriately as "discovery" items.
