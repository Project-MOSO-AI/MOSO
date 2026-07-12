import argparse
import glob
import logging
import os
from pathlib import Path
from typing import Optional

from moso_core.memory.vector_store import StoreEntry, VectorStore

logger = logging.getLogger(__name__)

def chunk_text(text: str, size: int = 500, overlap: int = 50) -> list[str]:
    words = text.split()
    chunks = []
    for i in range(0, len(words), max(1, size - overlap)):
        chunks.append(" ".join(words[i : i + size]))
        if i + size >= len(words):
            break
    return chunks

def ingest_folder(folder_path: str, category: str, db_path: Optional[str] = None):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        logger.error("sentence-transformers not installed. Run: pip install sentence-transformers")
        return

    model = SentenceTransformer("all-MiniLM-L6-v2")
    def embedder(text: str) -> list[float]:
        return model.encode(text).tolist()

    db_path = db_path or os.path.join(os.path.expanduser("~"), ".moso", "vector_store.db")
    store = VectorStore(db_path=db_path, embedder=embedder)

    search_path = Path(folder_path)
    if not search_path.exists():
        logger.error(f"Folder not found: {folder_path}")
        return

    files = list(search_path.glob("**/*.txt")) + list(search_path.glob("**/*.md"))
    total_chunks = 0

    for file_path in files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.warning(f"Could not read {file_path}: {e}")
            continue

        chunks = chunk_text(content)
        for i, chunk in enumerate(chunks):
            chunk_id = f"{file_path.name}_chunk_{i}"
            entry = StoreEntry(
                id=chunk_id,
                text=chunk,
                metadata={"category": category, "source": file_path.name}
            )
            store.store(entry)
            total_chunks += 1
            
    logger.info(f"Ingested {total_chunks} chunks from {category}")
    print(f"Ingested {total_chunks} chunks from {category} into {db_path}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Ingest knowledge into MOSO VectorStore")
    parser.add_argument("folder", help="Path to folder containing documents")
    parser.add_argument("--category", default="general", help="Category for the knowledge")
    parser.add_argument("--db", default=None, help="Path to vector_store.db")
    args = parser.parse_args()
    
    ingest_folder(args.folder, args.category, args.db)
