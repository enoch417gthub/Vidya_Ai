# scripts/init_db.py
# Run once to create all database tables: python scripts/init_db.py
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.database import engine, Base
from app.db import models  # Import models so SQLAlchemy registers them


def init_database():
    print('Initializing VIDYA AI database...')
    # Create all tables defined in models.py
    # safe=True equivalent: won't overwrite existing tables
    Base.metadata.create_all(bind=engine)
    print('Database tables created successfully!')
    print('Tables:', list(Base.metadata.tables.keys()))


if __name__ == '__main__':
    init_database()