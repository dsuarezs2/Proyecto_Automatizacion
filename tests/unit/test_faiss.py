import os
import unittest
import tempfile
import numpy as np
from unittest.mock import patch
from langchain_core.embeddings import Embeddings
from src.rag.rag_manager import RAGManager, FallbackRAGManager

class FakeEmbeddings(Embeddings):
    def __init__(self, size: int = 768):
        self.size = size

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.1 * (i % 10) for i in range(self.size)] for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.1 * (i % 10) for i in range(self.size)]

class TestFAISSIndexing(unittest.TestCase):
    def test_faiss_building_and_in_memory_search(self):
        """Test building the FAISS index in-memory and searching it."""
        embeddings = FakeEmbeddings(size=768)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            rag = RAGManager(persist_dir=temp_dir, embeddings=embeddings)
            
            docs = [
                {"content": "Instructions for HP screen replacement. Use PART-SCREEN-HP.", "title": "display_repair_manual.md", "source": "display_repair_manual.md"},
                {"content": "Instructions for CPU fan and overheating. Use PART-FAN-CPU.", "title": "cooling_system_manual.md", "source": "cooling_system_manual.md"}
            ]
            
            rag.build_index_from_documents(docs, chunk_size=500, overlap=50)
            
            self.assertIsNotNone(rag.index)
            self.assertEqual(len(rag.metadata), 2)
            
            # Query
            results = rag.query("screen replacement", k=1)
            self.assertEqual(len(results), 1)
            self.assertIn("HP screen", results[0]["metadata"]["text"])

    def test_faiss_serialization_and_load(self):
        """Test that FAISS index can be saved to disk and loaded back."""
        embeddings = FakeEmbeddings(size=768)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            rag = RAGManager(persist_dir=temp_dir, embeddings=embeddings)
            
            docs = [
                {"content": "Instructions for HP screen replacement. Use PART-SCREEN-HP.", "title": "display_repair_manual.md", "source": "display_repair_manual.md"}
            ]
            rag.build_index_from_documents(docs)
            
            # Check files exist
            self.assertTrue(os.path.exists(os.path.join(temp_dir, "index.bin")))
            self.assertTrue(os.path.exists(os.path.join(temp_dir, "metadata.json")))
            
            # Load in a new RAGManager
            rag_new = RAGManager(persist_dir=temp_dir, embeddings=embeddings)
            success = rag_new.load_local()
            self.assertTrue(success)
            self.assertIsNotNone(rag_new.index)
            self.assertEqual(len(rag_new.metadata), 1)
            
            results = rag_new.query("screen", k=1)
            self.assertEqual(len(results), 1)
            self.assertIn("HP screen", results[0]["metadata"]["text"])

    @patch.dict(os.environ, {}, clear=True)
    def test_offline_fallback_tfidf(self):
        """Test that missing GEMINI_API_KEY triggers TF-IDF fallback."""
        # Find the actual manuals directory in the project
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        manuals_dir = os.path.join(project_root, "data/manuals")
        
        # Verify RAGManager instantiation without GEMINI_API_KEY
        with tempfile.TemporaryDirectory() as temp_dir:
            rag = RAGManager(persist_dir=temp_dir, manuals_dir=manuals_dir)
            self.assertTrue(rag.use_fallback)
            self.assertIsNotNone(rag.fallback_manager)
            
            # Query for "sobrecalentamiento"
            results = rag.query("sobrecalentamiento", k=1)
            self.assertTrue(len(results) > 0)
            self.assertIn("cooling_system_manual.md", results[0]["metadata"]["title"])
            self.assertTrue(
                "sobrecalienta" in results[0]["metadata"]["text"].lower() or 
                "cooling" in results[0]["metadata"]["text"].lower() or 
                "fan" in results[0]["metadata"]["text"].lower()
            )

    def test_empty_database_and_out_of_domain(self):
        """Test edge cases like empty database querying and out-of-domain terms."""
        embeddings = FakeEmbeddings(size=768)
        with tempfile.TemporaryDirectory() as temp_dir:
            rag = RAGManager(persist_dir=temp_dir, embeddings=embeddings)
            
            # Querying uninitialized index should raise ValueError or attempt load and fail
            with self.assertRaises(ValueError):
                rag.query("something", k=1)
                
            # Build empty index
            rag.build_index_from_documents([])
            self.assertIsNone(rag.index)
            self.assertEqual(len(rag.metadata), 0)

if __name__ == "__main__":
    unittest.main()
