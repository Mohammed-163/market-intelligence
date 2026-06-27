import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

Base = declarative_base()

class Account(Base):
    __tablename__ = 'accounts'
    id = Column(Integer, primary_key=True)
    platform = Column(String)
    username = Column(String)
    followers_count = Column(Integer, nullable=True)

class Post(Base):
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer)
    post_url = Column(String)
    caption = Column(Text)
    media_type = Column(String)
    timestamp = Column(String)

class Insight(Base):
    __tablename__ = 'ai_insights'
    id = Column(Integer, primary_key=True)
    target = Column(String)
    insight_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

engine = create_engine('sqlite:///market_data.db')
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
