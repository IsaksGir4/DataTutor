from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config.settings import settings
from app.repositories.models import Base

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_database() -> None:
    """Ensure the local development database has the pgvector schema."""
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.create_all(bind=connection)


init_database()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()