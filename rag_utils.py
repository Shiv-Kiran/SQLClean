import os
import glob
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class LocalRAG:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.documents = []
        self.tfidf_matrix = None

    def index_directory(self, repo_path):
        """Index all .md and .sql files in the given directory recursively."""
        patterns = ['**/*.md', '**/*.sql']
        files = []
        for pattern in patterns:
            files.extend(glob.glob(os.path.join(repo_path, pattern), recursive=True))

        self.documents = []
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Chunk the content into smaller pieces, e.g., by paragraphs or fixed size
                    chunks = self._chunk_text(content, chunk_size=500)
                    for chunk in chunks:
                        self.documents.append({
                            'content': chunk,
                            'source': file_path
                        })
            except Exception as e:
                print(f"Error reading {file_path}: {e}")

        if self.documents:
            contents = [doc['content'] for doc in self.documents]
            self.tfidf_matrix = self.vectorizer.fit_transform(contents)
        else:
            self.tfidf_matrix = None

    def _chunk_text(self, text, chunk_size=500):
        """Simple text chunking by characters."""
        chunks = []
        for i in range(0, len(text), chunk_size):
            chunks.append(text[i:i+chunk_size])
        return chunks

    def retrieve(self, query, top_k=5):
        """Retrieve top-k relevant documents based on cosine similarity."""
        if self.tfidf_matrix is None or len(self.documents) == 0:
            return []

        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix)[0]
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        results = []
        for idx in top_indices:
            if similarities[idx] > 0.1:  # Threshold to filter low similarity
                results.append(self.documents[idx])
        return results

# Global instance
rag_instance = LocalRAG()