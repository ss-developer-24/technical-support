"""
Researcher Agent - Performs web search and RAG-based retrieval
"""
import logging
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types
import os
import asyncio
from tavily import TavilyClient

from rag.rag_engine import RAGEngine

logger = logging.getLogger(__name__)

class ResearcherAgent:
    """
    Researcher Agent with Tavily web search and Vertex AI RAG capabilities
    """
    
    def __init__(self):
        """Initialize the Researcher agent"""
        # Initialize Google ADK client
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        
        self.client = genai.Client(api_key=api_key)
        self.model_id = os.getenv("RESEARCHER_MODEL", "gemini-2.5-flash-lite")
        
        # Initialize Tavily for web search
        tavily_key = os.getenv("TAVILY_API_KEY")
        self.tavily_client = TavilyClient(api_key=tavily_key) if tavily_key else None
        
        # Initialize RAG engine
        self.enable_rag = os.getenv("ENABLE_RAG", "true").lower() == "true"
        self.rag_engine = RAGEngine() if self.enable_rag else None
        
        logger.info(f"Researcher initialized - Model: {self.model_id}, RAG: {self.enable_rag}, Tavily: {self.tavily_client is not None}")
    
    async def research(self, question: str) -> Dict[str, Any]:
        """
        Perform research on a question using RAG first, then web search if RAG fails
        
        Args:
            question: The question to research
            
        Returns:
            Dict containing research results and sources
        """
        try:
            logger.info(f"Researching: {question[:100]}...")
            
            rag_results = []
            web_results = []
            
            # Try RAG first
            if self.rag_engine:
                rag_results = await self._rag_search(question)
                
            # Only perform web search if RAG returned no results or insufficient results
            if not rag_results and self.tavily_client:
                logger.info("RAG returned no results, falling back to web search...")
                web_results = await self._web_search(question)
            elif rag_results:
                logger.info(f"RAG found {len(rag_results)} results, skipping web search")
            
            # Synthesize research findings
            synthesized = await self._synthesize_research(
                question=question,
                rag_results=rag_results,
                web_results=web_results
            )
            
            return synthesized
            
        except Exception as e:
            logger.error(f"Error in research: {str(e)}")
            raise
    
    async def _rag_search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search using RAG engine (Vertex AI embeddings)
        """
        try:
            logger.info("Performing RAG search...")
            results = await self.rag_engine.search(query, top_k=5)
            logger.info(f"RAG search returned {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"RAG search error: {str(e)}")
            return []
    
    async def _web_search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search the web using Tavily
        """
        try:
            logger.info("Performing web search with Tavily...")
            
            # Run Tavily search in thread pool (it's synchronous)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.tavily_client.search(
                    query=query,
                    search_depth="advanced",
                    max_results=5,
                    include_answer=True
                )
            )
            
            results = []
            for result in response.get("results", []):
                results.append({
                    "content": result.get("content", ""),
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "score": result.get("score", 0),
                    "source": "web"
                })
            
            logger.info(f"Web search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Web search error: {str(e)}")
            return []
    
    async def _synthesize_research(
        self,
        question: str,
        rag_results: List[Dict[str, Any]],
        web_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Synthesize research findings from multiple sources
        """
        try:
            # Prepare context from all sources
            context_parts = []
            all_sources = []
            
            if rag_results:
                context_parts.append("=== Internal Documentation ===")
                for i, result in enumerate(rag_results[:3], 1):
                    context_parts.append(f"\n[RAG-{i}] {result.get('content', '')}")
                    metadata = result.get("metadata", {})
                    all_sources.append({
                        "type": "rag",
                        "title": result.get("title", f"Document {i}"),
                        "source": metadata.get("source", "Unknown Document"),
                        "document": metadata.get("source", "Unknown"),
                        "chunk_id": metadata.get("chunk_id", 0),
                        "content": result.get("content", "")[:200] + "...",
                        "score": result.get("score", 0)
                    })
            
            if web_results:
                context_parts.append("\n\n=== Web Sources ===")
                for i, result in enumerate(web_results[:3], 1):
                    context_parts.append(f"\n[WEB-{i}] {result.get('title', '')}")
                    context_parts.append(f"URL: {result.get('url', '')}")
                    context_parts.append(f"Content: {result.get('content', '')}\n")
                    all_sources.append({
                        "type": "web",
                        "title": result.get("title", f"Web Source {i}"),
                        "url": result.get("url", ""),
                        "content": result.get("content", "")[:200] + "...",
                        "score": result.get("score", 0)
                    })
            
            context = "\n".join(context_parts)
            
            if not context.strip():
                logger.warning("No research context available")
                return {
                    "context": "",
                    "sources": [],
                    "summary": "No research results found."
                }
            
            # Generate summary using LLM
            summary_prompt = f"""
Synthesize the following research findings into a coherent summary that addresses this question:

Question: {question}

Research Findings:
{context}

Provide a clear and concise summary that:
1. Highlights the most relevant information
2. Identifies key points from multiple sources
3. Notes any contradictions or gaps
"""
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model=self.model_id,
                    contents=summary_prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.3,
                        max_output_tokens=512
                    )
                )
            )
            
            return {
                "context": context,
                "sources": all_sources,
                "summary": response.text
            }
            
        except Exception as e:
            logger.error(f"Error synthesizing research: {str(e)}")
            # Return raw context if synthesis fails
            return {
                "context": context if 'context' in locals() else "",
                "sources": all_sources if 'all_sources' in locals() else [],
                "summary": "Error generating summary"
            }
    
    async def ingest_documents(self) -> Dict[str, Any]:
        """
        Ingest documents from GCS bucket for RAG
        """
        if not self.rag_engine:
            raise ValueError("RAG engine not initialized")
        
        try:
            logger.info("Starting document ingestion...")
            result = await self.rag_engine.ingest_from_gcs()
            logger.info(f"Document ingestion complete: {result}")
            return result
        except Exception as e:
            logger.error(f"Error ingesting documents: {str(e)}")
            raise
