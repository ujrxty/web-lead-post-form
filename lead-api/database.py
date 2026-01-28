import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean
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
    signed_up = Column(Boolean, default=False)
    signed_up_at = Column(DateTime, nullable=True)
    callback_scheduled = Column(Boolean, default=False)
    callback_scheduled_at = Column(DateTime, nullable=True)


def create_tables():
    """Create all tables in the database"""
    Base.metadata.create_all(bind=engine)

    # Run migrations for new columns on existing tables
    run_migrations()


def run_migrations():
    """Add new columns to existing tables if they don't exist"""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)

    # Check if leads table exists
    if 'leads' not in inspector.get_table_names():
        return

    # Get existing columns
    existing_columns = [col['name'] for col in inspector.get_columns('leads')]

    # Define new columns to add
    new_columns = []

    if 'signed_up' not in existing_columns:
        if DATABASE_URL.startswith("sqlite"):
            new_columns.append("ALTER TABLE leads ADD COLUMN signed_up BOOLEAN DEFAULT 0")
        else:
            new_columns.append("ALTER TABLE leads ADD COLUMN signed_up BOOLEAN DEFAULT FALSE")

    if 'signed_up_at' not in existing_columns:
        new_columns.append("ALTER TABLE leads ADD COLUMN signed_up_at TIMESTAMP NULL")

    if 'callback_scheduled' not in existing_columns:
        if DATABASE_URL.startswith("sqlite"):
            new_columns.append("ALTER TABLE leads ADD COLUMN callback_scheduled BOOLEAN DEFAULT 0")
        else:
            new_columns.append("ALTER TABLE leads ADD COLUMN callback_scheduled BOOLEAN DEFAULT FALSE")

    if 'callback_scheduled_at' not in existing_columns:
        new_columns.append("ALTER TABLE leads ADD COLUMN callback_scheduled_at TIMESTAMP NULL")

    # Execute migrations
    if new_columns:
        with engine.connect() as conn:
            for sql in new_columns:
                try:
                    conn.execute(text(sql))
                    conn.commit()
                    print(f"Migration executed: {sql}")
                except Exception as e:
                    print(f"Migration skipped (may already exist): {e}")


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
