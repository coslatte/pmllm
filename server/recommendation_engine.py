import json
import os
import sys
from typing import Dict, Any, List

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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
