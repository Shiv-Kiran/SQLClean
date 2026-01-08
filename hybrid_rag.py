import os
import glob
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import chromadb
from sentence_transformers import SentenceTransformer
import faiss
from collections import defaultdict

class TFIDFRAG:
    """TF-IDF based RAG for keyword-level retrieval."""
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.documents = []
        self.tfidf_matrix = None

    def index(self, documents):
        self.documents = documents
        if documents:
            contents = [doc['content'] for doc in documents]
            self.tfidf_matrix = self.vectorizer.fit_transform(contents)
        else:
            self.tfidf_matrix = None

    def retrieve(self, query, top_k=5):
        if self.tfidf_matrix is None or len(self.documents) == 0:
            return []
        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix)[0]
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        results = []
        for idx in top_indices:
            if similarities[idx] > 0.1:
                results.append((self.documents[idx], similarities[idx]))
        return results


class ChromaRAG:
    """Chroma-based RAG using BGE embeddings for semantic retrieval."""
    def __init__(self):
        self.embedder = SentenceTransformer('BAAI/bge-code-large')
        self.chroma_client = chromadb.EphemeralClient()
        self.collection = self.chroma_client.create_collection(name="sql_docs")
        self.id_to_doc = {}

    def index(self, documents):
        if documents:
            chunks = [doc['content'] for doc in documents]
            embeddings = self.embedder.encode(chunks)
            ids = [str(i) for i in range(len(documents))]
            self.collection.add(
                documents=chunks,
                embeddings=embeddings.tolist(),
                ids=ids
            )
            for i, doc in enumerate(documents):
                self.id_to_doc[i] = doc

    def retrieve(self, query, top_k=5):
        query_emb = self.embedder.encode([query])[0]
        results = self.collection.query(query_embeddings=[query_emb.tolist()], n_results=top_k)
        retrieved = []
        for id_str, dist in zip(results['ids'][0], results['distances'][0]):
            idx = int(id_str)
            sim = 1 - dist  # Convert distance to similarity
            retrieved.append((self.id_to_doc[idx], sim))
        return retrieved


class FAISSRAG:
    """FAISS-based RAG for fast vector similarity search."""
    def __init__(self):
        self.embedder = SentenceTransformer('BAAI/bge-code-large')
        self.dimension = 1024
        self.faiss_index = faiss.IndexFlatIP(self.dimension)
        self.id_to_doc = {}

    def index(self, documents):
        if documents:
            chunks = [doc['content'] for doc in documents]
            embeddings = self.embedder.encode(chunks)
            self.faiss_index.add(embeddings)
            for i, doc in enumerate(documents):
                self.id_to_doc[i] = doc

    def retrieve(self, query, top_k=5):
        query_emb = self.embedder.encode([query])[0].reshape(1, -1)
        distances, indices = self.faiss_index.search(query_emb, top_k)
        retrieved = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx != -1:
                sim = dist
                retrieved.append((self.id_to_doc[idx], sim))
        return retrieved


class HybridRAG:
    """Hybrid RAG combining TF-IDF, Chroma, and FAISS for best retrieval."""
    def __init__(self):
        self.tfidf_rag = TFIDFRAG()
        self.chroma_rag = ChromaRAG()
        self.faiss_rag = FAISSRAG()
        self.documents = []

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
            self.tfidf_rag.index(self.documents)
            self.chroma_rag.index(self.documents)
            self.faiss_rag.index(self.documents)

    def _chunk_text(self, text, chunk_size=500):
        """Simple text chunking by characters."""
        chunks = []
        for i in range(0, len(text), chunk_size):
            chunks.append(text[i:i+chunk_size])
        return chunks

    def retrieve(self, query, top_k=5):
        """Retrieve top-k relevant documents using all three RAGs and merge results."""
        if len(self.documents) == 0:
            return []

        all_results = []

        # TF-IDF retrieval (keyword-based)
        tfidf_results = self.tfidf_rag.retrieve(query, top_k)
        all_results.extend(tfidf_results)

        # Chroma retrieval (semantic via embeddings)
        chroma_results = self.chroma_rag.retrieve(query, top_k)
        all_results.extend(chroma_results)

        # FAISS retrieval (fast vector similarity)
        faiss_results = self.faiss_rag.retrieve(query, top_k)
        all_results.extend(faiss_results)

        # Merger: Aggregate scores by document content and source
        scores = defaultdict(list)
        for doc, sim in all_results:
            key = (doc['source'], doc['content'])
            scores[key].append(sim)

        # Average scores and sort
        avg_scores = {key: np.mean(sims) for key, sims in scores.items()}
        sorted_keys = sorted(avg_scores, key=avg_scores.get, reverse=True)[:top_k]

        results = []
        for key in sorted_keys:
            results.append({
                'content': key[1],
                'source': key[0]
            })

        return results


# Global instance for hybrid retrieval
hybrid_rag_instance = HybridRAG()
