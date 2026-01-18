"""
Vector store module - Pinecone integration
"""
import os
import pathlib
from typing import List, Dict, Any, Optional
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

# Load .env file from project root directory
env_path = pathlib.Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)
# If root directory doesn't have it, also try current directory (backward compatibility)
if not env_path.exists():
    load_dotenv()


class VectorStore:
    """Vector store class, encapsulates Pinecone operations"""
    
    def __init__(self) -> None:
        """Initialize vector store"""
        api_key = os.getenv('PINECONE_API_KEY')
        index_name = os.getenv('PINECONE_INDEX', 'lumina-sales-agent')
        
        if not api_key:
            raise ValueError("PINECONE_API_KEY environment variable not set")
        
        try:
            # Ensure no proxy environment variables interfere
            for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
                os.environ.pop(var, None)
            
            # Use simpler initialization method to avoid parameter conflicts
            self.pc = Pinecone(api_key=api_key)
            self.index_name = index_name
            
            # Check if index exists, create if it doesn't
            try:
                existing_indexes = [idx.name for idx in self.pc.list_indexes()]
            except Exception as e:
                print(f"Error listing indexes: {e}")
                existing_indexes = []
            
            if index_name not in existing_indexes:
                print(f"Creating new index: {index_name}")
                try:
                    self.pc.create_index(
                        name=index_name,
                        dimension=1536,  # Dimension of text-embedding-3-small
                        metric='dotproduct',  # Recommened for hybrid search
                        spec=ServerlessSpec(
                            cloud='aws',
                            region='us-east-1'
                        )
                    )
                    print(f"Index {index_name} created successfully, waiting for readiness...")
                    # Wait for index to be ready
                    import time
                    time.sleep(2)
                except Exception as e:
                    print(f"Error creating index (may already exist): {e}")
            
            self.index = self.pc.Index(index_name)
        except Exception as e:
            print(f"Failed to initialize Pinecone client: {e}")
            print("Note: Please check if PINECONE_API_KEY is correct and network connection is normal")
            raise
    
    def upsert(self, vectors: List[Dict[str, Any]], client_id: str = "demo") -> int:
        """
        Insert or update vectors (multi-tenant support, hybrid search)
        
        Args:
            vectors: List of vectors, each containing id, values, sparse_values (optional), metadata
            client_id: Client ID for multi-tenant isolation (default "demo")
        
        Returns:
            Number of successfully stored vectors
        """
        try:
            # Pinecone upsert format
            formatted_vectors = []
            for vec in vectors:
                metadata = vec.get("metadata", {})
                # Force add client_id to metadata (multi-tenant isolation)
                if "client_id" not in metadata:
                    metadata["client_id"] = client_id
                
                formatted_vector = {
                    "id": vec["id"],
                    "values": vec["values"],
                    "metadata": metadata
                }
                
                # Add sparse values if present
                if "sparse_values" in vec:
                    formatted_vector["sparse_values"] = vec["sparse_values"]
                
                formatted_vectors.append(formatted_vector)
            
            self.index.upsert(vectors=formatted_vectors)
            return len(formatted_vectors)
        except Exception as e:
            print(f"Vector storage failed: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def search(self, query_vector: List[float], sparse_vector: Optional[Dict[str, Any]] = None, top_k: int = 5, client_id: str = "demo", alpha: float = 0.5) -> List[Dict[str, Any]]:
        """
        Vector similarity search (multi-tenant support, hybrid search)
        
        Args:
            query_vector: Dense query vector
            sparse_vector: Sparse query vector (optional)
            top_k: Return top k results
            client_id: Client ID for multi-tenant isolation
            alpha: Weight for dense vs sparse. (Only used if sparse_vector provided. But Pinecone doesn't use alpha directly in query, it's used to scale vectors before query. 
                   Here we assume 'hybrid' means passing both if available).
                   Actually Pinecone Python client just takes `sparse_vector`. Weighting is usually done by scaling vectors. 
                   For simplicity here, we pass both if available.
        
        Returns:
            List of search results
        """
        try:
            # Prepare query arguments
            query_args = {
                "vector": query_vector,
                "top_k": top_k,
                "include_metadata": True,
                "filter": {"client_id": {"$eq": client_id}}
            }
            
            if sparse_vector:
                query_args["sparse_vector"] = sparse_vector

            results = self.index.query(**query_args)
            
            return [
                {
                    "id": match.id,
                    "score": match.score,
                    "metadata": match.metadata
                }
                for match in results.matches
            ]
        except Exception as e:
            print(f"Vector search failed: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def delete(self, ids: List[str]) -> bool:
        """
        Delete vectors
        
        Args:
            ids: List of vector IDs to delete
        
        Returns:
            Whether successful
        """
        try:
            self.index.delete(ids=ids)
            return True
        except Exception as e:
            print(f"Vector deletion failed: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get index statistics
        
        Returns:
            Statistics dictionary
        """
        try:
            stats = self.index.describe_index_stats()
            return {
                "total_vectors": stats.total_vector_count,
                "dimension": stats.dimension,
                "index_fullness": stats.index_fullness
            }
        except Exception as e:
            print(f"Failed to get statistics: {e}")
            return {}
