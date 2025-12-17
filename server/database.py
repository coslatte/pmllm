from __future__ import annotations

import json
import os
from datetime import datetime
from typing import List

from sqlalchemy import create_engine, Column, String, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# SQLite / external database setup
DEFAULT_DB_PATH = os.getenv("CHAT_DB_PATH", "./storage/local_app.db")
if DEFAULT_DB_PATH.startswith("./"):
    os.makedirs(os.path.dirname(DEFAULT_DB_PATH), exist_ok=True)

SQLALCHEMY_DATABASE_URL = (
    os.getenv("CHAT_DB_RUNTIME_URL")
    or os.getenv("CHAT_DB_URL")
    or f"sqlite:///{DEFAULT_DB_PATH}"
)

connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args=connect_args
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Models
class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    preferences = relationship("Preference", back_populates="user", uselist=False)
    chats = relationship("Chat", back_populates="user")


class Preference(Base):
    __tablename__ = "preferences"

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    fav_genres = Column(Text)  # Stored as JSON
    disliked_genres = Column(Text)  # Stored as JSON
    fav_artists = Column(Text)  # Stored as JSON
    disliked_artists = Column(Text)  # Stored as JSON
    liked_tags = Column(Text)  # Stored as JSON
    disliked_tags = Column(Text)  # Stored as JSON
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="preferences")

    def _set_list(self, field_name: str, values: List[str]):
        setattr(self, field_name, json.dumps(values))

    def _get_list(self, field_name: str) -> List[str]:
        val = getattr(self, field_name)
        if isinstance(val, str):
            return json.loads(val)
        return []

    def set_genres(self, genres: List[str]):
        self._set_list("fav_genres", genres)

    def get_genres(self) -> List[str]:
        return self._get_list("fav_genres")

    def set_disliked_genres(self, genres: List[str]):
        self._set_list("disliked_genres", genres)

    def get_disliked_genres(self) -> List[str]:
        return self._get_list("disliked_genres")

    def set_artists(self, artists: List[str]):
        self._set_list("fav_artists", artists)

    def get_artists(self) -> List[str]:
        return self._get_list("fav_artists")

    def set_disliked_artists(self, artists: List[str]):
        self._set_list("disliked_artists", artists)

    def get_disliked_artists(self) -> List[str]:
        return self._get_list("disliked_artists")

    def set_liked_tags(self, tags: List[str]):
        self._set_list("liked_tags", tags)

    def get_liked_tags(self) -> List[str]:
        return self._get_list("liked_tags")

    def set_disliked_tags(self, tags: List[str]):
        self._set_list("disliked_tags", tags)

    def get_disliked_tags(self) -> List[str]:
        return self._get_list("disliked_tags")


class Chat(Base):
    __tablename__ = "chats"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat")


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, index=True)
    chat_id = Column(String, ForeignKey("chats.id"))
    role = Column(String)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    chat = relationship("Chat", back_populates="messages")


def init_db():
    Base.metadata.create_all(bind=engine)
