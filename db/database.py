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
    last_got_flat = Column(DateTime, nullable=True)


class FlatRecord(Base):
    __tablename__ = "flat_records"
    
    id = Column(Integer, primary_key=True, index=True)
    flat_url = Column(String, unique=True, index=True)
    title = Column(String)
    price = Column(String)
    location = Column(String)
    created_at = Column(DateTime)
    created_at_pretty = Column(String)
    image_url = Column(String, nullable=True)
    description = Column(String)
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


def get_pending_tasks(db) -> List[MonitoringTask]:
    """
    Retrieve tasks where the last_got_flat is either None or older than DEFAULT_LAST_MINUTES_GETTING.
    """
    time_threshold = datetime.now() - timedelta(minutes=settings.DEFAULT_LAST_MINUTES_GETTING)
    tasks = db.query(MonitoringTask).filter(
        (MonitoringTask.last_got_flat == None) | 
        (MonitoringTask.last_got_flat < time_threshold)
    ).all()
    return tasks


def update_last_got_flat(db, chat_id: str):
    """Update the last_got_flat timestamp for a given chat ID."""
    task = get_task_by_chat_id(db, chat_id)
    if task:
        task.last_got_flat = datetime.now()
        db.commit()

def get_flats_to_send_for_task(db, task: MonitoringTask) -> List[FlatRecord]:
    """
    Get a list of FlatRecords that should be sent for a given MonitoringTask.
    If the task has a 'last_got_flat' timestamp, return flats seen after that time.
    Otherwise, return flats seen in the last DEFAULT_LAST_MINUTES_GETTING minutes.
    """
    flats_query = db.query(FlatRecord)

    if task.last_got_flat:
        flats_to_send = flats_query.filter(
            FlatRecord.first_seen > task.last_got_flat
        ).all()
    else:
        time_threshold = datetime.now() - timedelta(minutes=settings.DEFAULT_LAST_MINUTES_GETTING)
        flats_to_send = flats_query.filter(
            FlatRecord.first_seen > time_threshold
        ).all()

    return flats_to_send
