import json
import os
import numpy as np
from typing import List, Dict, Any

class SimpleVectorStore:
    def __init__(self, storage_path):
        self.storage_path = storage_path
        self.data = [] # List of {id, text, embedding, metadata}
        self.load()

    def load(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                    self.data = raw_data
            except Exception as e:
                print(f"Error loading vector store: {e}")
                self.data = []

    def save(self):
        try:
            # Convert numpy arrays to lists if needed (though we store as lists in JSON)
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving vector store: {e}")

    def add_document(self, doc_id: str, text: str, embedding: List[float], metadata: Dict[str, Any] = None):
        # Check if exists and update
        for item in self.data:
            if item['id'] == doc_id:
                item['text'] = text
                item['embedding'] = embedding
                item['metadata'] = metadata or {}
                self.save()
                return

        self.data.append({
            "id": doc_id,
            "text": text,
            "embedding": embedding,
            "metadata": metadata or {}
        })
        self.save()

    def search(self, query_embedding: List[float], top_k: int = 3):
        if not self.data:
            return []

        query_vec = np.array(query_embedding)
        results = []

        for item in self.data:
            doc_vec = np.array(item['embedding'])
            # Cosine similarity
            norm_q = np.linalg.norm(query_vec)
            norm_d = np.linalg.norm(doc_vec)
            
            if norm_q == 0 or norm_d == 0:
                score = 0
            else:
                score = np.dot(query_vec, doc_vec) / (norm_q * norm_d)
            
            results.append((score, item))

        # Sort by score desc
        results.sort(key=lambda x: x[0], reverse=True)
        return results[:top_k]
