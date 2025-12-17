import os
import sys
import uuid
from typing import Dict, List, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.database import SessionLocal, init_db, User, Preference, Chat, Message
from server.milvus_handler import upsert_user_profile, get_user_profile_vector
from server.recommendation_engine import (
    generate_recommendations_for_user,
    recommend_albums_by_genres,
    recommend_albums_by_preferences,
)
from server.query_engine import run_semantic_query

# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Initialize DB on startup
        init_db()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise
    yield


app = FastAPI(
    title="PMLLM API",
    description="API for Music Recommendation RAG System",
    lifespan=lifespan,
)

# Configure CORS for frontend access
# Read allowed origins from environment or use defaults
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Pydantic Models
class UserCreate(BaseModel):
    username: str


class UserResponse(BaseModel):
    id: str
    username: str
    created_at: datetime

    class Config:
        from_attributes = True


class PreferencesInput(BaseModel):
    user_id: str
    fav_genres: List[str] = []
    disliked_genres: List[str] = []
    fav_artists: List[str] = []
    disliked_artists: List[str] = []
    liked_tags: List[str] = []
    disliked_tags: List[str] = []


class PreferencesResponse(BaseModel):
    user_id: str
    fav_genres: List[str]
    disliked_genres: List[str]
    fav_artists: List[str]
    disliked_artists: List[str]
    liked_tags: List[str]
    disliked_tags: List[str]
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChatCreate(BaseModel):
    user_id: str


class ChatResponse(BaseModel):
    id: str
    user_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class MessageInput(BaseModel):
    chat_id: str
    role: str
    content: str


class MessageResponse(BaseModel):
    id: str
    chat_id: str
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class QueryRequest(BaseModel):
    question: str
    chat_id: str | None = None
    top_k: int = Field(default=8, ge=1, le=20)
    debug: bool = False


class ArtistTagItem(BaseModel):
    node_id: str
    artist_name: str
    matched_terms: List[str]
    tags: List[str]
    genres: List[str]


class ArtistTagSearch(BaseModel):
    term: str
    match_count: int
    items: List[ArtistTagItem]


class SongItem(BaseModel):
    node_id: str
    song_name: str
    artist_name: Optional[str] = None
    album_name: Optional[str] = None
    duration_ms: Optional[int] = None
    duration_formatted: str = "N/A"
    tags: List[str] = Field(default_factory=list)


class AlbumItem(BaseModel):
    node_id: str
    album_name: str
    artist_name: Optional[str] = None
    release_date: Optional[str] = None
    track_count: int = 0
    tags: List[str] = Field(default_factory=list)


class ArtistDetailItem(BaseModel):
    node_id: str
    artist_name: str
    area: Optional[str] = None
    begin_date: Optional[str] = None
    end_date: Optional[str] = None
    artist_type: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    genres: List[str] = Field(default_factory=list)
    album_count: int = 0
    song_count: int = 0


class CollaborationItem(BaseModel):
    artist1_name: str
    artist2_name: str
    recording_name: str
    recording_id: str


class QueryDebugInfo(BaseModel):
    prompt: str
    context_sections: List[str]
    graph_context: List[str]
    vector_hits: List[Dict[str, object]]
    tag_term: Optional[str]


class QueryAnswer(BaseModel):
    answer: str
    context: List[str]
    latency_ms: float
    query_type: str = "general"
    artist_tag_search: Optional[ArtistTagSearch] = None
    songs: List[SongItem] = Field(default_factory=list)
    albums: List[AlbumItem] = Field(default_factory=list)
    artists: List[ArtistDetailItem] = Field(default_factory=list)
    collaborations: List[CollaborationItem] = Field(default_factory=list)
    debug: Optional[QueryDebugInfo] = None


class AlbumRecommendationRequest(BaseModel):
    user_id: Optional[str] = None
    include_genres: List[str] = Field(default_factory=list)
    exclude_genres: List[str] = Field(default_factory=list)
    limit: int = Field(default=12, ge=1, le=50)
    min_genre_overlap: int = Field(default=1, ge=1, le=10)


class AlbumRecommendationItem(BaseModel):
    release_id: str
    release_name: str
    release_group_name: Optional[str] = None
    artists: List[str] = Field(default_factory=list)
    matched_genres: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    connections: List[str] = Field(default_factory=list)
    matched_count: int
    score: float


class AlbumRecommendationResponse(BaseModel):
    generated_from: List[str]
    exclude_filters: List[str]
    recommendations: List[AlbumRecommendationItem]


# Music metadata models for preference selection
class GenreInfo(BaseModel):
    name: str
    count: int = 0
    description: Optional[str] = None


class TagInfo(BaseModel):
    name: str
    count: int = 0
    description: Optional[str] = None


class ArtistInfo(BaseModel):
    name: str
    genres: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    popularity_score: Optional[float] = None


class MusicMetadataResponse(BaseModel):
    genres: List[GenreInfo]
    tags: List[TagInfo]
    artists: List[ArtistInfo]
    total_genres: int
    total_tags: int
    total_artists: int


# Enhanced recommendation models
class PersonalizedRecommendationRequest(BaseModel):
    """Request for personalized album recommendations based on full user preferences."""
    user_id: Optional[str] = None
    include_genres: List[str] = Field(default_factory=list)
    exclude_genres: List[str] = Field(default_factory=list)
    include_artists: List[str] = Field(default_factory=list)
    exclude_artists: List[str] = Field(default_factory=list)
    include_tags: List[str] = Field(default_factory=list)
    exclude_tags: List[str] = Field(default_factory=list)
    limit: int = Field(default=12, ge=1, le=50)


class PersonalizedAlbumItem(BaseModel):
    """An album recommendation with detailed match information."""
    release_id: str
    release_name: str
    release_group_name: Optional[str] = None
    artists: List[str] = Field(default_factory=list)
    matched_artists: List[str] = Field(default_factory=list)
    all_genres: List[str] = Field(default_factory=list)
    matched_genres: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    matched_tags: List[str] = Field(default_factory=list)
    genre_match_count: int = 0
    artist_match_count: int = 0
    tag_match_count: int = 0
    score: float
    match_reasons: List[str] = Field(default_factory=list)


class PersonalizedRecommendationResponse(BaseModel):
    """Response containing personalized album recommendations."""
    preferences_used: Dict[str, List[str]]
    total_matches: int
    recommendations: List[PersonalizedAlbumItem]


# Helper to generate profile text
def generate_profile_text(
    fav_genres: List[str],
    disliked_genres: List[str],
    fav_artists: List[str],
    disliked_artists: List[str],
    liked_tags: List[str],
    disliked_tags: List[str],
) -> str:
    parts = []
    if fav_genres:
        parts.append(f"likes {', '.join(fav_genres)} music")
    if disliked_genres:
        parts.append(f"dislikes {', '.join(disliked_genres)} music")
    if fav_artists:
        parts.append(f"favorite artists include {', '.join(fav_artists)}")
    if disliked_artists:
        parts.append(f"dislikes artists like {', '.join(disliked_artists)}")
    if liked_tags:
        parts.append(f"interested in {', '.join(liked_tags)}")
    if disliked_tags:
        parts.append(f"not interested in {', '.join(disliked_tags)}")

    if not parts:
        return "User has no specific musical preferences listed."

    return "User " + ", ".join(parts) + "."


# Endpoints


@app.post("/users", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    new_user = User(id=str(uuid.uuid4()), username=user.username)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/preferences")
async def update_preferences(prefs: PreferencesInput, db: Session = Depends(get_db)):
    # Check if user exists
    user = db.query(User).filter(User.id == prefs.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update or create preferences
    db_prefs = db.query(Preference).filter(Preference.user_id == prefs.user_id).first()
    if not db_prefs:
        db_prefs = Preference(user_id=prefs.user_id)
        db.add(db_prefs)

    db_prefs.set_genres(prefs.fav_genres)
    db_prefs.set_disliked_genres(prefs.disliked_genres)
    db_prefs.set_artists(prefs.fav_artists)
    db_prefs.set_disliked_artists(prefs.disliked_artists)
    db_prefs.set_liked_tags(prefs.liked_tags)
    db_prefs.set_disliked_tags(prefs.disliked_tags)
    db.commit()

    # Generate text description
    profile_text = generate_profile_text(
        prefs.fav_genres,
        prefs.disliked_genres,
        prefs.fav_artists,
        prefs.disliked_artists,
        prefs.liked_tags,
        prefs.disliked_tags,
    )

    # Update Milvus
    try:
        await upsert_user_profile(prefs.user_id, profile_text)
    except Exception as e:
        print(f"Error updating Milvus: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to update vector store: {str(e)}"
        )

    return {
        "status": "success",
        "message": "Preferences updated and vector store synchronized",
        "profile_text": profile_text,
    }


@app.get("/preferences", response_model=PreferencesResponse)
def get_preferences(user_id: str = Query(..., description="User ID"), db: Session = Depends(get_db)):
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db_prefs = db.query(Preference).filter(Preference.user_id == user_id).first()
    
    if not db_prefs:
        return {
            "user_id": user_id,
            "fav_genres": [],
            "disliked_genres": [],
            "fav_artists": [],
            "disliked_artists": [],
            "liked_tags": [],
            "disliked_tags": [],
            "updated_at": None
        }

    return {
        "user_id": db_prefs.user_id,
        "fav_genres": db_prefs.get_genres(),
        "disliked_genres": db_prefs.get_disliked_genres(),
        "fav_artists": db_prefs.get_artists(),
        "disliked_artists": db_prefs.get_disliked_artists(),
        "liked_tags": db_prefs.get_liked_tags(),
        "disliked_tags": db_prefs.get_disliked_tags(),
        "updated_at": db_prefs.updated_at
    }


@app.get("/get_profile_vector")
async def get_profile(user_id: str):
    data = await get_user_profile_vector(user_id)
    if not data:
        raise HTTPException(status_code=404, detail="Profile vector not found")
    return data


@app.post("/chat", response_model=ChatResponse)
def create_chat(chat_input: ChatCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == chat_input.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_chat = Chat(id=str(uuid.uuid4()), user_id=chat_input.user_id)
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)
    return new_chat


@app.post("/message", response_model=MessageResponse)
def add_message(msg_input: MessageInput, db: Session = Depends(get_db)):
    chat = db.query(Chat).filter(Chat.id == msg_input.chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    new_message = Message(
        id=str(uuid.uuid4()),
        chat_id=msg_input.chat_id,
        role=msg_input.role,
        content=msg_input.content,
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    return new_message


@app.get("/chat/{chat_id}/messages", response_model=List[MessageResponse])
def get_chat_messages(chat_id: str, db: Session = Depends(get_db)):
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    return chat.messages


@app.post("/recommendations")
async def get_recommendations(user_id: str = Query(..., description="Target user id"), db: Session = Depends(get_db)):
    """Return RAG-based recommendations for a user profile.

    Handles common failure modes (missing preferences, Milvus outages, LLM errors)
    and surfaces actionable HTTP errors instead of crashing the server.
    """

    prefs = db.query(Preference).filter(Preference.user_id == user_id).first()
    if not prefs:
        raise HTTPException(status_code=404, detail="User preferences not found. Update /preferences first.")

    user_prefs = {
        "fav_genres": prefs.get_genres(),
        "disliked_genres": prefs.get_disliked_genres(),
        "fav_artists": prefs.get_artists(),
        "disliked_artists": prefs.get_disliked_artists(),
        "liked_tags": prefs.get_liked_tags(),
        "disliked_tags": prefs.get_disliked_tags(),
    }

    if not any(user_prefs.values()):
        raise HTTPException(
            status_code=400,
            detail="User preferences are empty. Add at least one preference before requesting recommendations.",
        )

    try:
        vector_data = await get_user_profile_vector(user_id)
    except Exception as exc:
        # Milvus outages should degrade gracefully instead of killing the API.
        print(f"Error retrieving profile vector for {user_id}: {exc}")
        vector_data = None

    if vector_data and vector_data.get("text"):
        profile_text = vector_data["text"]
    else:
        profile_text = generate_profile_text(
            user_prefs["fav_genres"],
            user_prefs["disliked_genres"],
            user_prefs["fav_artists"],
            user_prefs["disliked_artists"],
            user_prefs["liked_tags"],
            user_prefs["disliked_tags"],
        )

    try:
        return generate_recommendations_for_user(profile_text, user_prefs)
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=f"LLM timeout: {exc}") from exc
    except Exception as exc:
        print(f"Error generating recommendations for {user_id}: {exc}")
        raise HTTPException(status_code=502, detail="Failed to generate recommendations. Try again later.") from exc


@app.post("/recommendations/albums", response_model=AlbumRecommendationResponse)
def get_album_recommendations(
    payload: AlbumRecommendationRequest, db: Session = Depends(get_db)
):
    include_genres = [genre.strip() for genre in payload.include_genres if genre and genre.strip()]
    exclude_genres = [genre.strip() for genre in payload.exclude_genres if genre and genre.strip()]

    # Try to load user preferences if no genres provided in request
    if payload.user_id and not include_genres:
        user = db.query(User).filter(User.id == payload.user_id).first()
        if user:
            prefs = db.query(Preference).filter(Preference.user_id == user.id).first()
            if prefs:
                include_genres = prefs.get_genres()
        # Note: We don't raise 404 if user not found - we just use the provided genres

    include_original = sorted({genre for genre in include_genres if genre})
    exclude_original = sorted({genre for genre in exclude_genres if genre})

    include_lower = [genre.lower() for genre in include_original]
    exclude_lower = [genre.lower() for genre in exclude_original]

    if not include_lower:
        raise HTTPException(
            status_code=400,
            detail="No genres provided. Supply include_genres or set preferences for the user.",
        )

    try:
        recommendations = recommend_albums_by_genres(
            include_lower,
            exclude_lower,
            limit=payload.limit,
            min_overlap=min(payload.min_genre_overlap, len(include_lower)),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        print(f"Error querying Neo4j for album recommendations: {exc}")
        raise HTTPException(status_code=502, detail="Graph lookup failed. Try again later.") from exc

    return AlbumRecommendationResponse(
        generated_from=include_original,
        exclude_filters=exclude_original,
        recommendations=[AlbumRecommendationItem(**item) for item in recommendations],
    )


@app.post("/recommendations/personalized", response_model=PersonalizedRecommendationResponse)
def get_personalized_recommendations(
    payload: PersonalizedRecommendationRequest, db: Session = Depends(get_db)
):
    """Get personalized album recommendations based on user preferences.
    
    This endpoint uses all preference types (genres, artists, tags) to find
    the most relevant albums. It can either use preferences from the request
    or load them from the user's stored preferences.
    
    If no preferences are provided and user doesn't exist, returns discovery
    recommendations instead of an error.
    """
    include_genres = [g.strip() for g in payload.include_genres if g and g.strip()]
    exclude_genres = [g.strip() for g in payload.exclude_genres if g and g.strip()]
    include_artists = [a.strip() for a in payload.include_artists if a and a.strip()]
    exclude_artists = [a.strip() for a in payload.exclude_artists if a and a.strip()]
    include_tags = [t.strip() for t in payload.include_tags if t and t.strip()]
    exclude_tags = [t.strip() for t in payload.exclude_tags if t and t.strip()]

    # If user_id provided, try to load preferences from database
    # But don't fail if user doesn't exist or DB has issues - use request preferences instead
    if payload.user_id:
        try:
            user = db.query(User).filter(User.id == payload.user_id).first()
            if user:
                prefs = db.query(Preference).filter(Preference.user_id == user.id).first()
                if prefs:
                    # Only use stored preferences if none were provided in the request
                    if not include_genres:
                        include_genres = prefs.get_genres()
                    if not exclude_genres:
                        exclude_genres = prefs.get_disliked_genres()
                    if not include_artists:
                        include_artists = prefs.get_artists()
                    if not exclude_artists:
                        exclude_artists = prefs.get_disliked_artists()
                    if not include_tags:
                        include_tags = prefs.get_liked_tags()
                    if not exclude_tags:
                        exclude_tags = prefs.get_disliked_tags()
            # Note: We don't raise 404 if user not found - we just use the provided preferences
        except Exception as e:
            # Database query failed - log and continue with request preferences
            print(f"Warning: Failed to load user preferences from database: {e}")
            # Don't fail the request - just use whatever preferences were provided

    # If no preferences provided, we'll use an empty search which will trigger
    # the fallback discovery mode in recommend_albums_by_preferences
    use_discovery_mode = not include_genres and not include_artists and not include_tags

    try:
        recommendations = recommend_albums_by_preferences(
            include_genres=include_genres,
            exclude_genres=exclude_genres,
            include_artists=include_artists,
            exclude_artists=exclude_artists,
            include_tags=include_tags,
            exclude_tags=exclude_tags,
            limit=payload.limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        print(f"Error querying Neo4j for personalized recommendations: {exc}")
        raise HTTPException(status_code=502, detail="Graph lookup failed. Try again later.") from exc

    preferences_used = {
        "include_genres": include_genres,
        "exclude_genres": exclude_genres,
        "include_artists": include_artists,
        "exclude_artists": exclude_artists,
        "include_tags": include_tags,
        "exclude_tags": exclude_tags,
    }

    return PersonalizedRecommendationResponse(
        preferences_used=preferences_used,
        total_matches=len(recommendations),
        recommendations=[PersonalizedAlbumItem(**item) for item in recommendations],
    )


@app.get("/metadata/music", response_model=MusicMetadataResponse)
def get_music_metadata(
    genre_limit: int = Query(default=30, ge=1, le=100, description="Max genres to return"),
    tag_limit: int = Query(default=30, ge=1, le=100, description="Max tags to return"),
    artist_limit: int = Query(default=20, ge=1, le=50, description="Max artists to return"),
):
    """Get available genres, tags, and artists for user preference selection.
    
    This endpoint queries the Neo4j knowledge graph to retrieve popular
    music metadata that users can select as preferences.
    Note: In this database, genres are stored as Tags.
    """
    from db.neo4j.neo4j_handler import query_graph
    
    genres: List[GenreInfo] = []
    tags: List[TagInfo] = []
    artists: List[ArtistInfo] = []
    total_genres = 0
    total_tags = 0
    total_artists = 0
    
    try:
        # Query genres (stored as Tags in this database) with count
        # Filter to common music genre-like tags
        genre_query = """
        MATCH (t:Tag)
        OPTIONAL MATCH (t)-[r]-(release:Release)
        WITH t, count(release) AS release_count
        WHERE release_count > 0
        RETURN t.name AS name, release_count AS count
        ORDER BY release_count DESC
        LIMIT $limit
        """
        genre_rows = query_graph(genre_query, {"limit": genre_limit})
        genres = [
            GenreInfo(name=row["name"], count=row.get("count", 0))
            for row in genre_rows if row.get("name")
        ]
        
        # Get total tag count (used as genres)
        total_genre_query = "MATCH (t:Tag)-[r]-(release:Release) WITH t, count(release) AS c WHERE c > 0 RETURN count(DISTINCT t) AS total"
        total_genre_result = query_graph(total_genre_query, {})
        total_genres = total_genre_result[0]["total"] if total_genre_result else 0
        
    except Exception as e:
        print(f"Error fetching genres: {e}")
    
    try:
        # Query all tags with count (same as genres in this database)
        tag_query = """
        MATCH (t:Tag)
        OPTIONAL MATCH (t)-[r]-(entity)
        WITH t, count(entity) AS entity_count
        RETURN t.name AS name, entity_count AS count
        ORDER BY entity_count DESC
        LIMIT $limit
        """
        tag_rows = query_graph(tag_query, {"limit": tag_limit})
        tags = [
            TagInfo(name=row["name"], count=row.get("count", 0))
            for row in tag_rows if row.get("name")
        ]
        
        # Get total tag count
        total_tag_query = "MATCH (t:Tag) RETURN count(t) AS total"
        total_tag_result = query_graph(total_tag_query, {})
        total_tags = total_tag_result[0]["total"] if total_tag_result else 0
        
    except Exception as e:
        print(f"Error fetching tags: {e}")
    
    try:
        # Query popular artists with their tags (tags serve as genres in this database)
        artist_query = """
        MATCH (a:Artist)
        OPTIONAL MATCH (a)-[tr]-(t:Tag)
        WITH a, 
             collect(DISTINCT t.name) AS tags
        WHERE size(tags) > 0
        RETURN a.name AS name, tags AS genres, tags
        ORDER BY size(tags) DESC
        LIMIT $limit
        """
        artist_rows = query_graph(artist_query, {"limit": artist_limit})
        artists = [
            ArtistInfo(
                name=row["name"],
                genres=[g for g in row.get("genres", []) if g],
                tags=[t for t in row.get("tags", []) if t]
            )
            for row in artist_rows if row.get("name")
        ]
        
        # Get total artist count
        total_artist_query = "MATCH (a:Artist) RETURN count(a) AS total"
        total_artist_result = query_graph(total_artist_query, {})
        total_artists = total_artist_result[0]["total"] if total_artist_result else 0
        
    except Exception as e:
        print(f"Error fetching artists: {e}")
    
    return MusicMetadataResponse(
        genres=genres,
        tags=tags,
        artists=artists,
        total_genres=total_genres,
        total_tags=total_tags,
        total_artists=total_artists,
    )


@app.post("/query", response_model=QueryAnswer)
async def query_assistant(payload: QueryRequest, db: Session = Depends(get_db)):
    chat = None
    if payload.chat_id:
        chat = db.query(Chat).filter(Chat.id == payload.chat_id).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")

    start_time = datetime.utcnow()
    try:
        result = run_semantic_query(
            payload.question, top_k=payload.top_k, include_debug=payload.debug
        )
    except Exception as exc:
        print(f"Error running semantic query: {exc}")
        raise HTTPException(status_code=502, detail="Semantic search failed. Try again later.") from exc

    latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

    if chat:
        user_message = Message(
            id=str(uuid.uuid4()),
            chat_id=chat.id,
            role="user",
            content=payload.question,
        )
        assistant_message = Message(
            id=str(uuid.uuid4()),
            chat_id=chat.id,
            role="assistant",
            content=result.answer,
        )
        db.add_all([user_message, assistant_message])
        db.commit()

    artist_payload = None
    if result.tag_term:
        artist_payload = ArtistTagSearch(
            term=result.tag_term,
            match_count=len(result.tag_matches),
            items=[
                ArtistTagItem(
                    node_id=match.node_id,
                    artist_name=match.artist_name,
                    matched_terms=match.matched_terms,
                    tags=match.tags,
                    genres=match.genres,
                )
                for match in result.tag_matches
            ],
        )

    # Build song items
    song_items = [
        SongItem(
            node_id=s.node_id,
            song_name=s.song_name,
            artist_name=s.artist_name,
            album_name=s.album_name,
            duration_ms=s.duration_ms,
            duration_formatted=s._format_duration(),
            tags=s.tags,
        )
        for s in result.song_matches
    ]

    # Build album items
    album_items = [
        AlbumItem(
            node_id=a.node_id,
            album_name=a.album_name,
            artist_name=a.artist_name,
            release_date=a.release_date,
            track_count=a.track_count,
            tags=a.tags,
        )
        for a in result.album_matches
    ]

    # Build artist detail items
    artist_items = [
        ArtistDetailItem(
            node_id=a.node_id,
            artist_name=a.artist_name,
            area=a.area,
            begin_date=a.begin_date,
            end_date=a.end_date,
            artist_type=a.artist_type,
            tags=a.tags,
            genres=a.genres,
            album_count=a.album_count,
            song_count=a.song_count,
        )
        for a in result.artist_matches
    ]

    # Build collaboration items
    collab_items = [
        CollaborationItem(
            artist1_name=c.artist1_name,
            artist2_name=c.artist2_name,
            recording_name=c.recording_name,
            recording_id=c.recording_id,
        )
        for c in result.collaboration_matches
    ]

    debug_payload = None
    if result.debug:
        debug_payload = QueryDebugInfo(
            prompt=result.debug.prompt,
            context_sections=result.debug.context_sections,
            graph_context=result.debug.graph_context,
            vector_hits=result.debug.vector_hits,
            tag_term=result.debug.tag_term,
        )

    return QueryAnswer(
        answer=result.answer,
        context=result.context,
        latency_ms=latency_ms,
        query_type=result.query_type,
        artist_tag_search=artist_payload,
        songs=song_items,
        albums=album_items,
        artists=artist_items,
        collaborations=collab_items,
        debug=debug_payload,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
