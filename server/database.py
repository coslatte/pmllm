import json
from datetime import datetime
from typing import List, Optional

from sqlalchemy import create_engine, Column, String, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# SQLite setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./local_app.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
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
    fav_artists = Column(Text)  # Stored as JSON
    fav_instruments = Column(Text)  # Stored as JSON
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="preferences")

    def set_genres(self, genres: List[str]):
        self.fav_genres = json.dumps(genres)

    def get_genres(self) -> List[str]:
        return json.loads(self.fav_genres) if self.fav_genres else []

    def set_artists(self, artists: List[str]):
        self.fav_artists = json.dumps(artists)

    def get_artists(self) -> List[str]:
        return json.loads(self.fav_artists) if self.fav_artists else []

    def set_instruments(self, instruments: List[str]):
        self.fav_instruments = json.dumps(instruments)

    def get_instruments(self) -> List[str]:
        return json.loads(self.fav_instruments) if self.fav_instruments else []


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
