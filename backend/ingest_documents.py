#!/usr/bin/env python3
"""
Script to trigger document ingestion into ChromaDB
Can be run locally or deployed to Cloud Run as a one-time job
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from rag.rag_engine import RAGEngine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Ingest documents from GCS bucket into ChromaDB"""
    try:
        logger.info("Initializing RAG engine...")
        rag_engine = RAGEngine()
        
        logger.info(f"ChromaDB collection: {rag_engine.collection_name}")
        logger.info(f"Current document count: {rag_engine.collection.count()}")
        
        logger.info("Starting document ingestion from GCS...")
        result = await rag_engine.ingest_from_gcs()
        
        logger.info(f"Ingestion complete!")
        logger.info(f"  - Documents processed: {result.get('count', 0)}")
        logger.info(f"  - PDF files: {result.get('pdf_files_processed', 0)}")
        logger.info(f"  - Total documents in collection: {result.get('total_documents', 0)}")
        
        # Verify by doing a test search
        logger.info("\nTesting RAG search...")
        results = await rag_engine.search("virtual host requirements", top_k=3)
        logger.info(f"Test search returned {len(results)} results")
        
        if results:
            logger.info("\nSample result:")
            logger.info(f"  Score: {results[0]['score']:.3f}")
            logger.info(f"  Source: {results[0]['metadata'].get('source', 'N/A')}")
            logger.info(f"  Content preview: {results[0]['content'][:200]}...")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error during ingestion: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
