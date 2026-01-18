"""
Data ingestion module - Responsible for web crawling and vectorization
"""
import os
import pathlib
import traceback
import logging
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
from openai import AzureOpenAI
from dotenv import load_dotenv
from pinecone_text.sparse import BM25Encoder
from playwright.sync_api import sync_playwright
from markdownify import markdownify as md

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Clear proxy environment variables before loading environment variables
proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']
for var in proxy_vars:
    os.environ.pop(var, None)

# Load .env file from project root directory
env_path = pathlib.Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)
if not env_path.exists():
    load_dotenv()


class DataIngestion:
    """Data ingestion class, responsible for crawling web content and vectorization"""
    
    def __init__(self, vector_store) -> None:
        """
        Initialize data ingestion
        
        Args:
            vector_store: VectorStore instance for storing vectors
        """
        self.vector_store = vector_store
        
        # Ensure no proxy environment variables interfere
        for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
            os.environ.pop(var, None)
        
        # Use httpx client, but do not pass proxies parameter
        import httpx
        http_client = httpx.Client(
            timeout=httpx.Timeout(60.0, connect=10.0),
        )
        
        azure_api_key = os.getenv('AZURE_OPENAI_API_KEY')
        azure_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        azure_api_version = os.getenv('AZURE_OPENAI_API_VERSION', '2024-12-01-preview')
        
        self.openai_client = AzureOpenAI(
            api_key=azure_api_key,
            api_version=azure_api_version,
            azure_endpoint=azure_endpoint,
            http_client=http_client
        )
        
        # Initialize BM25 Encoder for sparse vectors
        # In production, this should be fit on a representative corpus and saved/loaded
        self.bm25 = BM25Encoder.default()
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def fetch_url(self, url: str) -> Optional[str]:
        """
        Fetch web page content using Playwright (handles dynamic content)
        Falls back to requests if Playwright fails.
        """
        html_content = None
        
        # Try Playwright first
        try:
            logger.info(f"Attempting to fetch {url} using Playwright...")
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until='networkidle', timeout=30000)
                html_content = page.content()
                browser.close()
            logger.info("Successfully fetched with Playwright")
            return html_content
        except Exception as e:
            logger.warning(f"Playwright fetch failed: {e}. Falling back to requests.")
            
        # Fallback to requests
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Failed to fetch URL {url} with requests: {e}")
            return None
    
    def extract_text(self, html: str) -> str:
        """
        Extract content from HTML and convert to Markdown.
        Uses markdownify for better structural preservation.
        """
        try:
            # Pre-clean with BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove unwanted tags
            for tag in soup(["script", "style", "meta", "link", "noscript", "svg", "iframe", "ad", "ins"]):
                tag.decompose()

            # Identify main content container if possible (heuristic)
            main_content = soup.find('main') or soup.find('article') or soup.find('div', id='content') or soup.find('div', class_='content')
            
            target_html = str(main_content) if main_content else str(soup.body or soup)
            
            # Convert to Markdown
            markdown_text = md(target_html, heading_style="ATX", strip=['a', 'img']) # Strip links/images to keep pure text for RAG
            
            # Clean up excessive newlines
            lines = [line.strip() for line in markdown_text.splitlines()]
            # Join with newline to preserve structure (headers, lists)
            clean_text = '\n'.join(line for line in lines if line)
            
            return clean_text
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            return ""
    
    def recursive_chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """
        Recursively split text by separators to keep semantic units together.
        Separators: ["\n\n", "\n", ". ", " ", ""]
        """
        separators = ["\n\n", "\n", ". ", " ", ""]
        
        def split_text(text: str, separators: List[str]) -> List[str]:
            final_chunks = []
            
            if len(text) <= chunk_size:
                return [text]
            
            if not separators:
                # If no separators left, force split by character
                return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size - overlap)]
            
            # Try to split by the first separator
            separator = separators[0]
            splits = text.split(separator)
            
            current_chunk = ""
            for split in splits:
                # Re-add separator loss (approximation)
                next_piece = split + separator if separator not in ["\n\n", "\n"] else split
                
                if len(current_chunk) + len(next_piece) > chunk_size:
                    if current_chunk:
                        final_chunks.append(current_chunk.strip())
                    current_chunk = next_piece
                else:
                    current_chunk += next_piece
            
            if current_chunk:
                final_chunks.append(current_chunk.strip())
                
            # If any chunk is still too big, accept it? Or recurse?
            # For simplicity in this demo, we accept (or could recurse with next separator)
            # Let's verify if chunks are valid.
            validated_chunks = []
            for chunk in final_chunks:
                if len(chunk) > chunk_size:
                    # Recurse with next separator
                    validated_chunks.extend(split_text(chunk, separators[1:]))
                else:
                    validated_chunks.append(chunk)
            
            return validated_chunks

        # Initial call
        return split_text(text, separators)
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Get embedding vectors for texts
        
        Args:
            texts: List of texts
        
        Returns:
            List of embedding vectors
        """
        try:
            embedding_deployment = os.getenv('AZURE_DEPLOYMENT_EMBEDDING', 'text-embedding-3-small')
            response = self.openai_client.embeddings.create(
                model=embedding_deployment,
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            print(f"Failed to get embeddings: {e}")
            return []
    
    def get_sparse_vector(self, text: str) -> Dict[str, Any]:
        """
        Get sparse vector (BM25) for text
        """
        try:
            return self.bm25.encode_documents(text)
        except Exception as e:
            print(f"Failed to get sparse vector: {e}")
            return {"indices": [], "values": []}

    def get_sparse_vector_query(self, text: str) -> Dict[str, Any]:
        """
        Get sparse vector for query
        """
        try:
            return self.bm25.encode_queries(text)
        except Exception as e:
            print(f"Failed to get sparse query vector: {e}")
            return {"indices": [], "values": []}

    def ingest_url(self, url: str, client_id: str = "demo") -> Dict[str, Any]:
        """Ingest URL content and vectorize"""
        try:
            # 1. Fetch web page content (Dynamic)
            html = self.fetch_url(url)
            if html is None:
                return {"success": False, "message": "Unable to fetch content", "url": url}
            
            # 2. Extract text (Markdown)
            text = self.extract_text(html)
            if not text:
                return {"success": False, "message": "Unable to extract text", "url": url}
            
            # 3. Recursive Chunking
            chunks = self.recursive_chunk_text(text)
            logger.info(f"Generated {len(chunks)} chunks for {url}")
            
            # 4. Generate Embeddings (Dense)
            embeddings = self.get_embeddings(chunks)
            if not embeddings:
                return {"success": False, "message": "Unable to generate embeddings", "url": url}
            
            # 5. Store to Vector DB (Hybrid)
            vectors_to_store = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                sparse_vector = self.get_sparse_vector(chunk)
                vectors_to_store.append({
                    "id": f"{url}_{i}",
                    "values": embedding,
                    "sparse_values": sparse_vector,
                    "metadata": {
                        "client_id": client_id,
                        "url": url,
                        "chunk_index": i,
                        "text": chunk
                    }
                })
            
            count = self.vector_store.upsert(vectors_to_store, client_id=client_id)
            
            return {
                "success": True,
                "message": "Data ingestion successful",
                "url": url,
                "chunks": len(chunks),
                "stored": count
            }
        except Exception as e:
            logger.error(f"Error in ingest_url: {e}")
            traceback.print_exc()
            return {
                "success": False,
                "message": f"Data ingestion failed: {str(e)}",
                "url": url
            }
