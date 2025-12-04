import os
import sys
import uuid
from typing import Dict, List, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.database import SessionLocal, init_db, User, Preference, Chat, Message
from server.milvus_handler import upsert_user_profile, get_user_profile_vector
from server.recommendation_engine import generate_recommendations_for_user
from server.query_engine import run_semantic_query

# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB on startup
    init_db()
    yield


app = FastAPI(
    title="PMLLM API",
    description="API for Music Recommendation RAG System",
    lifespan=lifespan,
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
    fav_genres: List[str]
    fav_artists: List[str]
    fav_instruments: List[str]


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
    artist_tag_search: Optional[ArtistTagSearch] = None
    debug: Optional[QueryDebugInfo] = None


# Helper to generate profile text
def generate_profile_text(
    genres: List[str], artists: List[str], instruments: List[str]
) -> str:
    parts = []
    if genres:
        parts.append(f"likes {', '.join(genres)} music")
    if artists:
        parts.append(f"favorite artists include {', '.join(artists)}")
    if instruments:
        parts.append(f"enjoys listening to {', '.join(instruments)}")

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
    db_prefs.set_artists(prefs.fav_artists)
    db_prefs.set_instruments(prefs.fav_instruments)
    db.commit()

    # Generate text description
    profile_text = generate_profile_text(
        prefs.fav_genres, prefs.fav_artists, prefs.fav_instruments
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
async def get_recommendations(user_id: str, db: Session = Depends(get_db)):
    # 1. Get user preferences from DB
    prefs = db.query(Preference).filter(Preference.user_id == user_id).first()
    if not prefs:
        raise HTTPException(status_code=404, detail="User preferences not found")

    user_prefs = {
        "fav_genres": prefs.get_genres(),
        "fav_artists": prefs.get_artists(),
        "fav_instruments": prefs.get_instruments(),
    }

    # 2. Get user profile text from Milvus (or regenerate it if missing)
    vector_data = await get_user_profile_vector(user_id)
    if vector_data and vector_data.get("text"):
        profile_text = vector_data["text"]
    else:
        # Fallback: generate text
        profile_text = generate_profile_text(
            user_prefs["fav_genres"],
            user_prefs["fav_artists"],
            user_prefs["fav_instruments"],
        )

    # 3. Generate recommendations
    try:
        recommendations = generate_recommendations_for_user(profile_text, user_prefs)
        return recommendations
    except Exception as e:
        print(f"Error generating recommendations: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error generating recommendations: {str(e)}"
        )


@app.post("/query", response_model=QueryAnswer)
async def query_assistant(payload: QueryRequest, db: Session = Depends(get_db)):
    chat = None
    if payload.chat_id:
        chat = db.query(Chat).filter(Chat.id == payload.chat_id).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")

    start_time = datetime.utcnow()
    result = run_semantic_query(
        payload.question, top_k=payload.top_k, include_debug=payload.debug
    )
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
        artist_tag_search=artist_payload,
        debug=debug_payload,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
