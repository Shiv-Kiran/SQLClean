"""
RAG Strategy Configuration and Selection
Allows switching between different RAG implementations:
- simple: LocalRAG (TF-IDF only)
- hybrid: HybridRAG (TF-IDF + Chroma + FAISS)
"""

from enum import Enum
from rag_utils import LocalRAG as SimpleLocalRAG
from hybrid_rag import HybridRAG, TFIDFRAG, ChromaRAG, FAISSRAG


class RAGStrategy(Enum):
    SIMPLE = "simple"      # TF-IDF only
    HYBRID = "hybrid"      # TF-IDF + Chroma + FAISS


class RAGFactory:
    """Factory for creating RAG instances based on strategy."""
    
    _instances = {}
    
    @staticmethod
    def create_rag(strategy: RAGStrategy = RAGStrategy.HYBRID):
        """
        Create a RAG instance based on strategy.
        
        Args:
            strategy: RAGStrategy enum value
            
        Returns:
            RAG instance (LocalRAG for SIMPLE, HybridRAG for HYBRID)
        """
        if strategy not in RAGFactory._instances:
            if strategy == RAGStrategy.SIMPLE:
                RAGFactory._instances[strategy] = SimpleLocalRAG()
            elif strategy == RAGStrategy.HYBRID:
                RAGFactory._instances[strategy] = HybridRAG()
            else:
                raise ValueError(f"Unknown RAG strategy: {strategy}")
        
        return RAGFactory._instances[strategy]
    
    @staticmethod
    def get_rag_info(strategy: RAGStrategy):
        """Get information about a RAG strategy."""
        info = {
            RAGStrategy.SIMPLE: {
                "name": "Simple TF-IDF RAG",
                "components": ["TF-IDF Vectorizer"],
                "use_case": "Keyword-based retrieval, lightweight, fast",
                "dependencies": ["scikit-learn", "numpy"],
                "pros": ["Fast", "Lightweight", "Works offline"],
                "cons": ["Keyword-only", "No semantic understanding"]
            },
            RAGStrategy.HYBRID: {
                "name": "Hybrid Multi-RAG",
                "components": [
                    "TF-IDF (keyword matching)",
                    "Chroma (semantic embeddings)",
                    "FAISS (fast vector search)"
                ],
                "use_case": "Best-of-both-worlds: keywords + semantics + speed",
                "dependencies": ["scikit-learn", "chromadb", "sentence-transformers", "faiss-cpu"],
                "pros": [
                    "Combines keyword and semantic search",
                    "Handles synonyms well",
                    "Fast retrieval",
                    "Score fusion for better results"
                ],
                "cons": ["Higher memory usage", "Slower indexing", "More dependencies"]
            }
        }
        return info.get(strategy, {})


# Default instances
default_rag = RAGFactory.create_rag(RAGStrategy.SIMPLE)
hybrid_rag = RAGFactory.create_rag(RAGStrategy.HYBRID)
