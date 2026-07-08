import os
import sys

# Add project root to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.rag.rag_manager import RAGManager

def main():
    manuals_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/manuals"))
    persist_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/faiss_store"))
    
    print("Bootstrapping FAISS Vector Store...")
    print(f"Manuals directory: {manuals_dir}")
    print(f"Persistence directory: {persist_dir}")
    
    if not os.path.exists(manuals_dir):
        print(f"Error: Manuals directory does not exist at {manuals_dir}")
        sys.exit(1)
        
    documents = []
    for filename in sorted(os.listdir(manuals_dir)):
        if filename.endswith(".md"):
            path = os.path.join(manuals_dir, filename)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            documents.append({
                "content": content,
                "title": filename,
                "source": path
            })
            
    print(f"Loaded {len(documents)} manuals.")
    
    # Initialize RAGManager
    rag = RAGManager(persist_dir=persist_dir, manuals_dir=manuals_dir)
    
    print("Building index from documents...")
    rag.build_index_from_documents(documents)
    print("Bootstrapping completed successfully.")

if __name__ == "__main__":
    main()
