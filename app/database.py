from databases import Database
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

print("✅ Loaded DATABASE_URL:", settings.DATABASE_URL)
from app.models.base import Base

# Database instance for async queries
database = Database(settings.DATABASE_URL)

# SQLAlchemy engine
engine = create_engine(settings.DATABASE_URL)

# SessionLocal for ORM operations
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    """Create all tables in the database"""
    Base.metadata.create_all(bind=engine)
    print("✅ All tables created successfully")


def drop_tables():
    """Drop all tables from the database"""
    Base.metadata.drop_all(bind=engine)
    print("❌ All tables dropped")


async def connect_db():
    """Connect to database on startup"""
    await database.connect()
    print("✅ Database connected")


async def disconnect_db():
    """Disconnect from database on shutdown"""
    await database.disconnect()
    print("❌ Database disconnected")


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Helper function to convert SQLAlchemy model to dict
def model_to_dict(obj):
    """Convert SQLAlchemy model instance to dictionary"""
    if obj is None:
        return None
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
