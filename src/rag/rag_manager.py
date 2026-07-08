import os
import json
import faiss
import numpy as np
from typing import List, Dict, Any, Tuple
import google.generativeai as genai
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from langchain_core.documents import Document

class FallbackRAGManager:
    def __init__(self, manuals_dir: str = "data/manuals"):
        self.manuals_dir = manuals_dir
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.chunks: List[Dict[str, Any]] = []
        self.tfidf_matrix = None
        if os.path.exists(self.manuals_dir):
            self.load_and_index_manuals()

    def load_and_index_manuals(self, chunk_size: int = 500, overlap: int = 50):
        """Loads and indexes the markdown manuals using TF-IDF."""
        documents = []
        if not os.path.exists(self.manuals_dir):
            return
        
        for filename in sorted(os.listdir(self.manuals_dir)):
            if filename.endswith(".md"):
                path = os.path.join(self.manuals_dir, filename)
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    documents.append({
                        "content": content,
                        "title": filename,
                        "source": path
                    })
        
        self.chunks = []
        for doc in documents:
            content = doc["content"]
            start = 0
            while start < len(content):
                end = start + chunk_size
                chunk = content[start:end]
                self.chunks.append({
                    "text": chunk,
                    "title": doc["title"],
                    "source": doc["source"],
                    "chunk_id": len(self.chunks)
                })
                start += (chunk_size - overlap)
        
        if self.chunks:
            texts = [c["text"] for c in self.chunks]
            self.tfidf_matrix = self.vectorizer.fit_transform(texts)

    def query(self, query_text: str, k: int = 2) -> List[Dict[str, Any]]:
        """Queries the local TF-IDF index for the top k documents."""
        if self.tfidf_matrix is None or not self.chunks:
            return []
        
        query_vec = self.vectorizer.transform([query_text])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        
        # Argsort returns ascending, so we reverse it
        top_indices = similarities.argsort()[::-1][:k]
        
        results = []
        for idx in top_indices:
            if similarities[idx] > 0.01:  # Low threshold for testing
                results.append({
                    "metadata": self.chunks[idx],
                    "score": float(similarities[idx])
                })
        return results

class RAGManager:
    def __init__(self, persist_dir: str = "data/faiss_store", embedding_model: str = "models/text-embedding-004", manuals_dir: str = "data/manuals", embeddings: Any = None):
        self.persist_dir = persist_dir
        self.embedding_model = embedding_model
        self.manuals_dir = manuals_dir
        self.embeddings = embeddings
        self.index = None
        self.metadata: List[Dict[str, Any]] = []
        self.use_fallback = False
        self.fallback_manager = None
        
        # Ensure directories exist
        os.makedirs(self.persist_dir, exist_ok=True)
        
        # Check if we should use fallback
        if self.embeddings is not None:
            # We are using custom/mock embeddings (usually during tests)
            self.use_fallback = False
        elif "GEMINI_API_KEY" in os.environ and os.environ["GEMINI_API_KEY"]:
            try:
                genai.configure(api_key=os.environ["GEMINI_API_KEY"])
            except Exception as e:
                print(f"[RAGManager] Gemini configure failed: {e}. Falling back to TF-IDF.")
                self.use_fallback = True
        else:
            print("[RAGManager] GEMINI_API_KEY not found. Falling back to TF-IDF.")
            self.use_fallback = True
            
        if self.use_fallback:
            self.fallback_manager = FallbackRAGManager(manuals_dir=self.manuals_dir)

    def _get_embedding(self, text: str) -> np.ndarray:
        """Helper to get a single vector embedding."""
        if self.embeddings is not None:
            if hasattr(self.embeddings, "embed_query"):
                emb = self.embeddings.embed_query(text)
            elif hasattr(self.embeddings, "embed_documents"):
                emb = self.embeddings.embed_documents([text])[0]
            else:
                emb = self.embeddings(text)
            return np.array(emb, dtype=np.float32)
            
        response = genai.embed_content(
            model=self.embedding_model,
            content=text,
            task_type="retrieval_document"
        )
        return np.array(response['embedding'], dtype=np.float32)

    def _get_embeddings(self, texts: List[str]) -> np.ndarray:
        """Helper to get a batch of embeddings."""
        if self.embeddings is not None:
            if hasattr(self.embeddings, "embed_documents"):
                embs = self.embeddings.embed_documents(texts)
            else:
                embs = [self._get_embedding(t) for t in texts]
            return np.array(embs, dtype=np.float32)
            
        try:
            response = genai.embed_content(
                model=self.embedding_model,
                content=texts,
                task_type="retrieval_document"
            )
            return np.array(response['embedding'], dtype=np.float32)
        except Exception:
            embs = [self._get_embedding(t) for t in texts]
            return np.array(embs, dtype=np.float32)

    def build_index_from_documents(self, documents: List[Dict[str, Any]], chunk_size: int = 500, overlap: int = 50):
        """Chunks input documents, embeds them, builds FAISS index and persists it."""
        if self.use_fallback:
            # Chunk and populate fallback manager
            chunks = []
            for doc in documents:
                content = doc["content"]
                source = doc.get("source", "")
                title = doc.get("title", "")
                
                start = 0
                while start < len(content):
                    end = start + chunk_size
                    chunk_text = content[start:end]
                    chunks.append({
                        "text": chunk_text,
                        "source": source,
                        "title": title,
                        "chunk_id": len(chunks)
                    })
                    start += (chunk_size - overlap)
            self.fallback_manager.chunks = chunks
            if chunks:
                texts = [c["text"] for c in chunks]
                self.fallback_manager.tfidf_matrix = self.fallback_manager.vectorizer.fit_transform(texts)
            return

        chunks = []
        texts = []
        for doc in documents:
            content = doc["content"]
            source = doc.get("source", "")
            title = doc.get("title", "")
            
            start = 0
            while start < len(content):
                end = start + chunk_size
                chunk_text = content[start:end]
                chunks.append({
                    "text": chunk_text,
                    "source": source,
                    "title": title,
                    "chunk_id": len(chunks)
                })
                texts.append(chunk_text)
                start += (chunk_size - overlap)
                
        if not texts:
            self.index = None
            self.metadata = []
            return

        embeddings_matrix = self._get_embeddings(texts)
        dimension = embeddings_matrix.shape[1]
        
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings_matrix)
        self.metadata = chunks
        
        self.save_local()

    def save_local(self):
        """Saves the FAISS index and metadata files to the persistence directory."""
        if self.use_fallback:
            return
        
        if self.index is not None:
            faiss.write_index(self.index, os.path.join(self.persist_dir, "index.bin"))
            with open(os.path.join(self.persist_dir, "metadata.json"), "w", encoding="utf-8") as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)

    def load_local(self) -> bool:
        """Loads FAISS index and metadata files from persistence directory."""
        if self.use_fallback:
            if self.fallback_manager:
                self.fallback_manager.load_and_index_manuals()
                return len(self.fallback_manager.chunks) > 0
            return False
            
        index_path = os.path.join(self.persist_dir, "index.bin")
        meta_path = os.path.join(self.persist_dir, "metadata.json")
        
        if os.path.exists(index_path) and os.path.exists(meta_path):
            try:
                self.index = faiss.read_index(index_path)
                with open(meta_path, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
                return True
            except Exception as e:
                print(f"[RAGManager] Failed to load local index: {e}")
                return False
        return False

    def query(self, query_text: str, k: int = 3) -> List[Dict[str, Any]]:
        """Queries the FAISS or fallback index for matching chunks."""
        if self.use_fallback:
            return self.fallback_manager.query(query_text, k)
            
        if self.index is None:
            if not self.load_local():
                raise ValueError("Index is not loaded or initialized.")
                
        query_vector = self._get_embedding(query_text).reshape(1, -1)
        distances, indices = self.index.search(query_vector, k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.metadata) and idx != -1:
                results.append({
                    "metadata": self.metadata[idx],
                    "score": float(distances[0][i])
                })
        return results

    def similarity_search_with_score(self, query: str, k: int = 3) -> List[Tuple[Document, float]]:
        """Compatibility method returning LangChain style Document object and score."""
        results = self.query(query, k)
        docs_and_scores = []
        for res in results:
            meta = res["metadata"]
            score = res["score"]
            text = meta.get("text", "")
            doc = Document(page_content=text, metadata=meta)
            docs_and_scores.append((doc, score))
        return docs_and_scores

    def similarity_search(self, query: str, k: int = 3) -> List[Document]:
        """Compatibility method returning LangChain style Document objects."""
        docs_and_scores = self.similarity_search_with_score(query, k)
        return [doc for doc, _ in docs_and_scores]
