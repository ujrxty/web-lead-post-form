import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Database URL - Use PostgreSQL in production, SQLite for local dev
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./leads.db")

# Fix for Render's PostgreSQL URL (they use postgres:// but SQLAlchemy needs postgresql://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create engine - different config for SQLite vs PostgreSQL
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


class Lead(Base):
    """Lead model representing submitted lead data"""
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    gender = Column(String(20), nullable=True)
    date_of_birth = Column(String(20), nullable=True)
    phone = Column(String(20), unique=True, index=True, nullable=False)
    mobile_phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    street = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    postal_code = Column(String(20), nullable=True)
    primary_insurance = Column(String(255), nullable=True)
    total_med_count = Column(Integer, nullable=True)
    list_affiliate_name = Column(String(255), nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    salesforce_status = Column(String(50), default="success")


def create_tables():
    """Create all tables in the database"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
