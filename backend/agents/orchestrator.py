"""
Orchestrator Agent - Coordinates between Researcher and Reviewer agents
"""
import logging
from typing import Dict, Any, Optional
from google import genai
from google.genai import types
import os
import asyncio

logger = logging.getLogger(__name__)

class OrchestratorAgent:
    """
    Orchestrator Agent manages the flow between Researcher and Reviewer agents
    """
    
    def __init__(self, researcher=None, reviewer=None):
        """Initialize the Orchestrator agent"""
        self.researcher = researcher
        self.reviewer = reviewer
        
        # Initialize Google ADK client
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        
        self.client = genai.Client(api_key=api_key)
        self.model_id = os.getenv("ORCHESTRATOR_MODEL", "gemini-pro")
        
        logger.info(f"Orchestrator initialized with model: {self.model_id}")
    
    async def process_query(
        self,
        question: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a user query by coordinating between agents
        
        Args:
            question: User's question
            session_id: Optional session identifier for context
            
        Returns:
            Dict containing answer and sources
        """
        try:
            logger.info(f"Orchestrator processing query: {question[:100]}...")
            
            # Step 1: Determine if research is needed
            needs_research = await self._analyze_query_requirements(question)
            
            research_results = None
            if needs_research:
                logger.info("Query requires research - invoking Researcher agent")
                research_results = await self.researcher.research(question)
            
            # Step 2: Generate initial response using research or direct knowledge
            response = await self._generate_response(
                question=question,
                research_results=research_results
            )
            
            # Step 3: Review the response for quality and accuracy
            logger.info("Sending response to Reviewer agent")
            reviewed_response = await self.reviewer.review(
                question=question,
                answer=response["answer"],
                sources=research_results.get("sources", []) if research_results else []
            )
            
            return {
                "answer": reviewed_response["answer"],
                "sources": reviewed_response.get("sources", []),
                "session_id": session_id,
                "metadata": {
                    "research_performed": needs_research,
                    "review_score": reviewed_response.get("quality_score")
                }
            }
            
        except Exception as e:
            logger.error(f"Error in orchestrator: {str(e)}")
            raise
    
    async def _analyze_query_requirements(self, question: str) -> bool:
        """
        Analyze if the query requires external research
        
        Returns:
            True if research is needed, False otherwise
        """
        try:
            analysis_prompt = f"""
Analyze the following question and determine if it requires external research or RAG-based information retrieval.

Question: {question}

Respond with JSON in the following format:
{{
    "needs_research": true/false,
    "reasoning": "brief explanation"
}}

Questions that need research:
- Specific technical product information
- Current documentation or specifications
- Troubleshooting guides for specific products
- Recent updates or changes
- Detailed how-to guides

Questions that don't need research:
- General technical concepts
- Common programming patterns
- Basic troubleshooting approaches
"""
            
            import json
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model=self.model_id,
                    contents=analysis_prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        response_mime_type="application/json"
                    )
                )
            )
            
            analysis = json.loads(response.text)
            return analysis.get("needs_research", True)
            
        except Exception as e:
            logger.warning(f"Error analyzing query requirements: {e}")
            # Default to needing research if analysis fails
            return True
    
    async def _generate_response(
        self,
        question: str,
        research_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate response using LLM with optional research context
        """
        try:
            if research_results and research_results.get("context"):
                # Use research context
                prompt = f"""
You are a helpful technical support assistant. Answer the following question using the provided research context.

Question: {question}

Research Context:
{research_results["context"]}

Provide a clear, accurate, and helpful answer. Reference specific information from the context when relevant.
"""
            else:
                # Use direct knowledge
                prompt = f"""
You are a helpful technical support assistant. Answer the following question to the best of your knowledge.

Question: {question}

Provide a clear, accurate, and helpful answer based on your general knowledge.
"""
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model=self.model_id,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.7,
                        max_output_tokens=1024
                    )
                )
            )
            
            return {
                "answer": response.text,
                "sources": research_results.get("sources", []) if research_results else []
            }
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise
