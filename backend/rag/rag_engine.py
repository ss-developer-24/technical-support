"""
RAG Engine for document embeddings and retrieval using Vertex AI + ChromaDB
"""
import logging
import os
from typing import List, Dict, Any
import asyncio
from google.cloud import storage
from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel
import numpy as np
import pdfplumber
import io
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)

class RAGEngine:
    """
    RAG Engine using Vertex AI for embeddings and ChromaDB for vector storage
    """
    
    def __init__(self):
        """Initialize RAG engine with Vertex AI embeddings and ChromaDB storage"""
        # GCP Configuration
        self.project_id = os.getenv("GCP_PROJECT_ID")
        self.location = os.getenv("VERTEX_AI_LOCATION", "us-central1")
        self.bucket_name = os.getenv("GCS_BUCKET_NAME")
        
        if not self.project_id or not self.bucket_name:
            raise ValueError("GCP_PROJECT_ID and GCS_BUCKET_NAME must be set")
        
        # Initialize Vertex AI
        aiplatform.init(project=self.project_id, location=self.location)
        
        # Initialize embedding model (using text-embedding-004)
        self.embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")
        
        # Storage client
        self.storage_client = storage.Client(project=self.project_id)
        self.bucket = self.storage_client.bucket(self.bucket_name)
        
        # Initialize ChromaDB with persistent storage
        chroma_persist_dir = os.getenv("CHROMA_PERSIST_DIR", "/tmp/chromadb")
        os.makedirs(chroma_persist_dir, exist_ok=True)
        
        self.chroma_client = chromadb.PersistentClient(
            path=chroma_persist_dir,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        self.collection_name = "technical_support_docs"
        try:
            self.collection = self.chroma_client.get_collection(name=self.collection_name)
            logger.info(f"Loaded existing ChromaDB collection with {self.collection.count()} documents")
        except:
            self.collection = self.chroma_client.create_collection(
                name=self.collection_name,
                metadata={"description": "Technical support documentation embeddings"}
            )
            logger.info(f"Created new ChromaDB collection: {self.collection_name}")
        
        logger.info(f"RAG Engine initialized - Project: {self.project_id}, Bucket: {self.bucket_name}, ChromaDB: {chroma_persist_dir}")
    
    def _get_embeddings_sync(self, texts: List[str]) -> List[List[float]]:
        """Synchronous wrapper for getting embeddings from Vertex AI"""
        embeddings = self.embedding_model.get_embeddings(texts)
        return [emb.values for emb in embeddings]
    
    async def ingest_from_gcs(self) -> Dict[str, Any]:
        """
        Ingest PDF documents from GCS bucket and create embeddings
        
        Returns:
            Dict with ingestion statistics
        """
        try:
            logger.info(f"Starting document ingestion from gs://{self.bucket_name}")
            
            # List all PDF files in bucket (run in thread pool)
            loop = asyncio.get_event_loop()
            blobs = await loop.run_in_executor(
                None,
                lambda: list(self.bucket.list_blobs())
            )
            pdf_blobs = [b for b in blobs if b.name.lower().endswith('.pdf')]
            
            logger.info(f"Found {len(pdf_blobs)} PDF files")
            
            if not pdf_blobs:
                return {"count": 0, "message": "No PDF files found in bucket"}
            
            # Process each PDF
            new_documents = []
            for idx, blob in enumerate(pdf_blobs):
                try:
                    logger.info(f"Processing {idx+1}/{len(pdf_blobs)}: {blob.name}")
                    logger.info(f"About to call _process_pdf_blob for: {blob.name}")
                    docs = await self._process_pdf_blob(blob)
                    logger.info(f"_process_pdf_blob returned {len(docs)} docs for: {blob.name}")
                    new_documents.extend(docs)
                    logger.info(f"Successfully processed {blob.name}, total docs so far: {len(new_documents)}")
                except Exception as e:
                    logger.error(f"Error processing {blob.name}: {str(e)}", exc_info=True)
            
            if not new_documents:
                return {"count": 0, "message": "No content extracted from PDFs"}
            
            # Generate embeddings for new documents
            logger.info(f"Generating embeddings for {len(new_documents)} document chunks...")
            embeddings = await self._generate_embeddings(
                [doc["content"] for doc in new_documents]
            )
            
            # Add to ChromaDB collection
            logger.info(f"Adding {len(new_documents)} documents to ChromaDB...")
            
            # Prepare data for ChromaDB
            ids = [f"doc_{i}_{hash(doc['content'][:100])}" for i, doc in enumerate(new_documents)]
            documents_text = [doc["content"] for doc in new_documents]
            metadatas = [
                {
                    "source": doc["metadata"]["source"],
                    "chunk_id": str(doc["metadata"]["chunk_id"]),
                    "total_chunks": str(doc["metadata"]["total_chunks"]),
                    "type": doc["metadata"]["type"],
                    "title": doc["title"]
                }
                for doc in new_documents
            ]
            
            # Add to ChromaDB in batches to avoid memory issues
            batch_size = 100
            for i in range(0, len(new_documents), batch_size):
                batch_end = min(i + batch_size, len(new_documents))
                logger.info(f"Adding batch {i//batch_size + 1} ({i}-{batch_end})...")
                
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda start=i, end=batch_end: self.collection.add(
                        ids=ids[start:end],
                        embeddings=embeddings[start:end],
                        documents=documents_text[start:end],
                        metadatas=metadatas[start:end]
                    )
                )
            
            total_count = self.collection.count()
            logger.info(f"Successfully ingested {len(new_documents)} document chunks. Total in collection: {total_count}")
            
            return {
                "count": len(new_documents),
                "total_documents": total_count,
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
            logger.info(f"ENTERED _process_pdf_blob for: {blob.name}")
            
            # Run the entire PDF processing in a thread executor to avoid blocking
            loop = asyncio.get_event_loop()
            documents = await loop.run_in_executor(
                None,
                self._extract_pdf_sync,
                blob
            )
            
            logger.info(f"Successfully extracted {len(documents)} chunks from {blob.name}")
            return documents
            
        except Exception as e:
            logger.error(f"Error processing PDF {blob.name}: {str(e)}")
            return []
    
    def _extract_pdf_sync(self, blob: storage.Blob) -> List[Dict[str, Any]]:
        """
        Synchronous PDF extraction (runs in thread pool)
        """
        logger.info(f"Downloading PDF: {blob.name}")
        pdf_bytes = blob.download_as_bytes()
        logger.info(f"Downloaded {len(pdf_bytes)} bytes for: {blob.name}")
        
        pdf_file = io.BytesIO(pdf_bytes)
        
        logger.info(f"Extracting text from PDF: {blob.name}")
        # Extract text and tables with pdfplumber
        full_text = ""
        
        with pdfplumber.open(pdf_file) as pdf:
            logger.info(f"Opened PDF, found {len(pdf.pages)} pages in: {blob.name}")
            
            for page_num, page in enumerate(pdf.pages):
                logger.info(f"Extracting page {page_num + 1}/{len(pdf.pages)} from: {blob.name}")
                
                # Extract text
                text = page.extract_text() or ""
                page_content = f"\n\n--- Page {page_num + 1} ---\n\n{text}"
                
                # Extract tables and format them
                tables = page.extract_tables()
                if tables:
                    logger.info(f"Found {len(tables)} tables on page {page_num + 1}")
                    for table_num, table in enumerate(tables):
                        page_content += f"\n\n[Table {table_num + 1}]\n"
                        # Format table as text with pipes for better structure
                        for row in table:
                            if row:  # Skip empty rows
                                page_content += " | ".join(str(cell or "") for cell in row) + "\n"
                
                full_text += page_content
                logger.info(f"Extracted {len(text)} chars from page {page_num + 1}")
        
        logger.info(f"Chunking text for: {blob.name} ({len(full_text)} chars)")
        # Chunk text (simple chunking by size)
        logger.info(f"About to call _chunk_text...")
        chunks = self._chunk_text(full_text, chunk_size=1000, overlap=200)
        logger.info(f"_chunk_text returned, processing {len(chunks)} chunks")
        
        logger.info(f"Created {len(chunks)} chunks from {blob.name}")
        logger.info(f"Building document objects...")
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
        
        logger.info(f"Returning {len(documents)} documents from _extract_pdf_sync")
        return documents
    
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
        max_iterations = (text_length // (chunk_size - overlap)) + 2  # Safety limit
        iterations = 0
        
        while start < text_length and iterations < max_iterations:
            iterations += 1
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
            
            # Ensure we're making progress
            next_start = end - overlap
            if next_start <= start:
                next_start = start + 1  # Force progress to avoid infinite loop
            start = next_start
        
        logger.info(f"_chunk_text completed: created {len(chunks)} chunks in {iterations} iterations")
        return chunks
        
        return chunks
    
    async def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts using Vertex AI
        
        Returns:
            List of embedding vectors as lists (compatible with ChromaDB)
        """
        try:
            # Vertex AI has batch limits, process in batches
            batch_size = 5
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                logger.info(f"Generating embeddings for batch {i//batch_size + 1} ({len(batch)} texts)...")
                
                # Run in thread pool (Vertex AI client is synchronous)
                loop = asyncio.get_event_loop()
                embeddings = await loop.run_in_executor(
                    None,
                    self._get_embeddings_sync,
                    batch
                )
                
                # Add embedding vectors as lists (ChromaDB compatible)
                all_embeddings.extend(embeddings)
            
            logger.info(f"Generated {len(all_embeddings)} embeddings")
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
        Search for relevant documents using semantic similarity via ChromaDB
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of relevant documents with scores
        """
        try:
            collection_count = self.collection.count()
            if collection_count == 0:
                logger.warning("No documents in ChromaDB collection, returning empty results")
                return []
            
            logger.info(f"Searching {collection_count} documents for: {query[:100]}...")
            
            # Generate query embedding
            query_embeddings = await self._generate_embeddings([query])
            query_vector = query_embeddings[0]
            
            # Query ChromaDB
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: self.collection.query(
                    query_embeddings=[query_vector],
                    n_results=top_k,
                    include=["documents", "metadatas", "distances"]
                )
            )
            
            # Format results
            formatted_results = []
            if results and results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    # ChromaDB returns distances (lower is better)
                    # Convert to similarity score (higher is better)
                    distance = results['distances'][0][i]
                    # For cosine distance: similarity = 1 - distance
                    similarity = 1 - distance
                    
                    # Only include results above threshold
                    if similarity > 0.3:
                        formatted_results.append({
                            "content": results['documents'][0][i],
                            "metadata": results['metadatas'][0][i],
                            "title": results['metadatas'][0][i].get('title', 'Untitled'),
                            "score": float(similarity)
                        })
            
            logger.info(f"Search returned {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error in search: {str(e)}")
            return []
