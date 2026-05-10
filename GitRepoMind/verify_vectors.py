#!/usr/bin/env python
"""
Verify that vectors are properly stored in Qdrant.
"""

import sys
sys.path.insert(0, 'd:\\wadinternal\\GitRepoMind\\server')
sys.path.insert(0, 'd:\\wadinternal\\GitRepoMind\\server\\src')

from src.services.vector_store_service import QdrantVectorStore

def main():
    print("=" * 80)
    print("Verifying Qdrant Vector Storage")
    print("=" * 80)
    
    try:
        vector_store = QdrantVectorStore()
        print(f"\n✓ Connected to Qdrant at {vector_store.url}")
        
        # Get collection info
        collection_info = vector_store.get_collection_info()
        print(f"\n📊 Collection: {collection_info['name']}")
        print(f"   Points stored: {collection_info['points_count']}")
        print(f"   Vectors count: {collection_info['vectors_count']}")
        
        # Test search with a sample query
        print("\n🔍 Testing semantic search...")
        sample_query = [0.1] * 384  # Sample 384-dim vector
        results = vector_store.search_similar(sample_query, top_k=3)
        print(f"   Found {len(results)} similar chunks")
        
        if results:
            print("\n📝 Sample search results (first 2):")
            for i, result in enumerate(results[:2]):
                print(f"\n   Result {i+1}:")
                print(f"     File: {result.get('file_path', 'N/A')}")
                print(f"     Score: {result.get('score', 'N/A')}")
                print(f"     Text preview: {result.get('text', 'N/A')[:100]}...")
        
        print("\n" + "=" * 80)
        print("✅ Vector Storage Verification Successful")
        print("=" * 80)
        return 0
        
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
