#!/usr/bin/env python3
"""Run one-off manual indexing pass on all Slack channels."""
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.rag import index_all_channels, get_document_count
from src.utils.logger import setup_logger

if __name__ == "__main__":
    setup_logger("INFO")
    print("Starting manual indexing of Slack channels into Vector Store...")
    count = index_all_channels()
    total = get_document_count()
    print(f"Indexing complete! Added {count} documents. Total in vector store: {total}")
