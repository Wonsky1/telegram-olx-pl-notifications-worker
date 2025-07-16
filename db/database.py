from datetime import datetime, timedelta
from typing import List, Tuple

from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from core.config import settings

DATABASE_URL = settings.DATABASE_URL


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class MonitoringTask(Base):
    __tablename__ = "monitoring_tasks"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, unique=True, index=True)
    url = Column(String, nullable=False)
    last_updated = Column(DateTime, nullable=False)
    last_got_item = Column(DateTime, nullable=True)


class ItemRecord(Base):
    __tablename__ = "item_records"
    
    id = Column(Integer, primary_key=True, index=True)
    item_url = Column(String, unique=True, index=True)
    title = Column(String)
    price = Column(String)
    location = Column(String)
    created_at = Column(DateTime)
    created_at_pretty = Column(String)
    image_url = Column(String, nullable=True)
    description = Column(String)
    source_url = Column(String, nullable=False)
    first_seen = Column(DateTime, default=datetime.now)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_task_by_chat_id(db, chat_id: str):
    """Fetch a monitoring task by chat ID."""
    return db.query(MonitoringTask).filter(MonitoringTask.chat_id == chat_id).first()


def create_task(db, chat_id: str, url: str):
    """Create a new monitoring task and store it in the database."""
    new_task = MonitoringTask(chat_id=chat_id, url=url, last_updated=datetime.now())
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


def delete_task_by_chat_id(db, chat_id: str):
    """Delete a monitoring task by chat ID."""
    task = get_task_by_chat_id(db, chat_id)
    if task:
        db.delete(task)
        db.commit()


def get_all_tasks(db):
    """Get all monitoring tasks from the database."""
    return db.query(MonitoringTask).all()
