import os
import pickle
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict

INDEX_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "faiss_index")
INDEX_PATH = os.path.join(INDEX_DIR, "index.faiss")
META_PATH = os.path.join(INDEX_DIR, "metadata.pkl")

class VectorStore:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.dimension = 384
        self.index = None
        self.metadata: List[Dict] = []
        self._load_if_exists()

    def _load_if_exists(self):
        if os.path.exists(INDEX_PATH) and os.path.exists(META_PATH):
            try:
                self.index = faiss.read_index(INDEX_PATH)
                with open(META_PATH, "rb") as f:
                    self.metadata = pickle.load(f)
            except Exception:
                self.index = faiss.IndexFlatL2(self.dimension)
                self.metadata = []
        else:
            self.index = faiss.IndexFlatL2(self.dimension)

    def add_chunks(self, chunks: List[Dict]):
        if not chunks:
            return
        texts = [c["text"] for c in chunks]
        embeddings = self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        # Ensure strict contiguous float32 format for FAISS
        embeddings = np.ascontiguousarray(embeddings, dtype=np.float32)
        
        if self.index is None:
            self.index = faiss.IndexFlatL2(self.dimension)
            
        self.index.add(embeddings)
        self.metadata.extend(chunks)

        os.makedirs(INDEX_DIR, exist_ok=True)
        faiss.write_index(self.index, INDEX_PATH)
        with open(META_PATH, "wb") as f:
            pickle.dump(self.metadata, f)

    def similarity_search(self, query: str, top_k: int = 3) -> List[Dict]:
        if self.index is None or self.index.ntotal == 0:
            return []
        query_emb = self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
        query_emb = np.ascontiguousarray(query_emb, dtype=np.float32)
        distances, indices = self.index.search(query_emb, top_k)

        results = []
        for idx in indices[0]:
            if 0 <= idx < len(self.metadata):
                results.append(self.metadata[idx])
        return results
