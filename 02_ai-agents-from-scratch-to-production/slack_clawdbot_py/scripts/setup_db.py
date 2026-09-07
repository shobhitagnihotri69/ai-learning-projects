#!/usr/bin/env python3
"""Database initialization script."""
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.memory.database import initialize_database, close_database
from src.utils.logger import setup_logger

if __name__ == "__main__":
    setup_logger("INFO")
    print("Initializing Slack Assistant Database...")
    initialize_database()
    close_database()
    print("Database setup complete! SQLite tables and indexes created.")
