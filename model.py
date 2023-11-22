from sqlalchemy import (
    Column,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./db.sqlite"
engine = create_engine(DATABASE_URL)
Base = declarative_base()

class Poll(Base):
    __tablename__ = "polls"

    id = Column(Integer, primary_key=True, index=True)
    poll_id = Column(Integer)
    chat_id = Column(Integer)
    message_id = Column(Integer)
    question = Column(String, nullable=False)
    options = Column(String, nullable=False)
    dows = Column(String, nullable=False)
    start_time = Column(String, nullable=False)
    end_time = Column(String, nullable=False)


class User(Base):
    __tablename__ = "users"

    poll_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    poll_question = Column(String, nullable=False)
    user_options = Column(String)



Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autoflush=True, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
