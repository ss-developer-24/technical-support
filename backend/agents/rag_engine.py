"""
RAG Engine for document embeddings and retrieval using Vertex AI
"""
import logging
import os
from typing import List, Dict, Any
import asyncio
from google.cloud import storage
from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel
import numpy as np
from PyPDF2 import PdfReader
import io
import pickle
import tempfile

logger = logging.getLogger(__name__)

class RAGEngine:
    """
    RAG Engine using Vertex AI for embeddings and vector search
    """
    
    def __init__(self):
        """Initialize RAG engine with Vertex AI"""
        # GCP Configuration
        self.project_id = os.getenv("GCP_PROJECT_ID")
        self.location = os.getenv("VERTEX_AI_LOCATION", "us-central1")
        self.bucket_name = os.getenv("GCS_BUCKET_NAME")
        
        if not self.project_id or not self.bucket_name:
            raise ValueError("GCP_PROJECT_ID and GCS_BUCKET_NAME must be set")
        
        # Initialize Vertex AI
        aiplatform.init(project=self.project_id, location=self.location)
        
        # Initialize embedding model
        self.embedding_model = TextEmbeddingModel.from_pretrained("textembedding-gecko@003")
        
        # Storage client
        self.storage_client = storage.Client(project=self.project_id)
        self.bucket = self.storage_client.bucket(self.bucket_name)
        
        # In-memory vector store (for production, use Vertex AI Vector Search)
        self.embeddings_cache_file = "/tmp/embeddings_cache.pkl"
        self.documents = []
        self.embeddings = []
        
        # Try to load cached embeddings
        self._load_cache()
        
        logger.info(f"RAG Engine initialized - Project: {self.project_id}, Bucket: {self.bucket_name}")
    
    def _load_cache(self):
        """Load cached embeddings from file"""
        try:
            if os.path.exists(self.embeddings_cache_file):
                with open(self.embeddings_cache_file, 'rb') as f:
                    cache = pickle.load(f)
                    self.documents = cache.get('documents', [])
                    self.embeddings = cache.get('embeddings', [])
                logger.info(f"Loaded {len(self.documents)} cached documents")
        except Exception as e:
            logger.warning(f"Could not load cache: {str(e)}")
    
    def _save_cache(self):
        """Save embeddings to cache file"""
        try:
            with open(self.embeddings_cache_file, 'wb') as f:
                pickle.dump({
                    'documents': self.documents,
                    'embeddings': self.embeddings
                }, f)
            logger.info("Embeddings cache saved")
        except Exception as e:
            logger.warning(f"Could not save cache: {str(e)}")
    
    async def ingest_from_gcs(self) -> Dict[str, Any]:
        """
        Ingest PDF documents from GCS bucket and create embeddings
        
        Returns:
            Dict with ingestion statistics
        """
        try:
            logger.info(f"Starting document ingestion from gs://{self.bucket_name}")
            
            # List all PDF files in bucket
            blobs = list(self.bucket.list_blobs())
            pdf_blobs = [b for b in blobs if b.name.lower().endswith('.pdf')]
            
            logger.info(f"Found {len(pdf_blobs)} PDF files")
            
            if not pdf_blobs:
                return {"count": 0, "message": "No PDF files found in bucket"}
            
            # Process each PDF
            new_documents = []
            for blob in pdf_blobs:
                try:
                    logger.info(f"Processing: {blob.name}")
                    docs = await self._process_pdf_blob(blob)
                    new_documents.extend(docs)
                except Exception as e:
                    logger.error(f"Error processing {blob.name}: {str(e)}")
            
            if not new_documents:
                return {"count": 0, "message": "No content extracted from PDFs"}
            
            # Generate embeddings for new documents
            logger.info(f"Generating embeddings for {len(new_documents)} document chunks...")
            new_embeddings = await self._generate_embeddings(
                [doc["content"] for doc in new_documents]
            )
            
            # Add to store
            self.documents.extend(new_documents)
            self.embeddings.extend(new_embeddings)
            
            # Save cache
            self._save_cache()
            
            logger.info(f"Successfully ingested {len(new_documents)} document chunks")
            
            return {
                "count": len(new_documents),
                "total_documents": len(self.documents),
                "pdf_files_processed": len(pdf_blobs)
            }
            
        except Exception as e:
            logger.error(f"Error in document ingestion: {str(e)}")
            raise
    
    async def _process_pdf_blob(self, blob: storage.Blob) -> List[Dict[str, Any]]:
        """
        Extract text from PDF blob and chunk it
        
        Returns:
            List of document chunks with metadata
        """
        try:
            # Download PDF to memory
            pdf_bytes = blob.download_as_bytes()
            pdf_file = io.BytesIO(pdf_bytes)
            
            # Extract text
            reader = PdfReader(pdf_file)
            full_text = ""
            
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                full_text += f"\n\n--- Page {page_num + 1} ---\n\n{text}"
            
            # Chunk text (simple chunking by size)
            chunks = self._chunk_text(full_text, chunk_size=1000, overlap=200)
            
            # Create document objects
            documents = []
            for i, chunk in enumerate(chunks):
                documents.append({
                    "content": chunk,
                    "metadata": {
                        "source": blob.name,
                        "chunk_id": i,
                        "total_chunks": len(chunks),
                        "type": "pdf"
                    },
                    "title": f"{blob.name} (chunk {i+1}/{len(chunks)})"
                })
            
            return documents
            
        except Exception as e:
            logger.error(f"Error processing PDF {blob.name}: {str(e)}")
            return []
    
    def _chunk_text(
        self,
        text: str,
        chunk_size: int = 1000,
        overlap: int = 200
    ) -> List[str]:
        """
        Split text into overlapping chunks
        """
        if not text:
            return []
        
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < text_length:
                # Look for period, question mark, or exclamation
                last_period = text.rfind('.', start, end)
                last_question = text.rfind('?', start, end)
                last_exclaim = text.rfind('!', start, end)
                
                break_point = max(last_period, last_question, last_exclaim)
                if break_point > start:
                    end = break_point + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
        
        return chunks
    
    async def _generate_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for a list of texts using Vertex AI
        """
        try:
            # Vertex AI has batch limits, process in batches
            batch_size = 5
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                
                # Run in thread pool (Vertex AI client is synchronous)
                loop = asyncio.get_event_loop()
                embeddings = await loop.run_in_executor(
                    None,
                    lambda: self.embedding_model.get_embeddings(batch)
                )
                
                # Extract vectors
                for emb in embeddings:
                    all_embeddings.append(np.array(emb.values))
            
            return all_embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            raise
    
    async def search(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant documents using semantic similarity
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of relevant documents with scores
        """
        try:
            if not self.documents or not self.embeddings:
                logger.warning("No documents in store, returning empty results")
                return []
            
            # Generate query embedding
            query_embeddings = await self._generate_embeddings([query])
            query_vector = query_embeddings[0]
            
            # Compute cosine similarity
            similarities = []
            for doc_vector in self.embeddings:
                similarity = self._cosine_similarity(query_vector, doc_vector)
                similarities.append(similarity)
            
            # Get top-k results
            top_indices = np.argsort(similarities)[-top_k:][::-1]
            
            results = []
            for idx in top_indices:
                if similarities[idx] > 0.3:  # Threshold for relevance
                    doc = self.documents[idx].copy()
                    doc['score'] = float(similarities[idx])
                    results.append(doc)
            
            logger.info(f"Search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error in search: {str(e)}")
            return []
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
