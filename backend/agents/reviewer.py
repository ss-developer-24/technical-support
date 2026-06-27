"""
Reviewer Agent - Reviews and validates responses
"""
import logging
from typing import Dict, Any, List
from google import genai
from google.genai import types
import os
import json
import asyncio

logger = logging.getLogger(__name__)

class ReviewerAgent:
    """
    Reviewer Agent validates and improves responses
    """
    
    def __init__(self):
        """Initialize the Reviewer agent"""
        # Initialize Google ADK client
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        
        self.client = genai.Client(api_key=api_key)
        self.model_id = os.getenv("REVIEWER_MODEL", "gemini-pro")
        
        logger.info(f"Reviewer initialized with model: {self.model_id}")
    
    async def review(
        self,
        question: str,
        answer: str,
        sources: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Review an answer for quality, accuracy, and completeness
        
        Args:
            question: Original question
            answer: Generated answer to review
            sources: Optional sources used to generate the answer
            
        Returns:
            Dict containing reviewed answer and quality metrics
        """
        try:
            logger.info("Reviewing answer...")
            
            # Perform quality assessment
            assessment = await self._assess_quality(question, answer, sources)
            
            # Check if answer has RAG sources (internal documentation)
            has_rag_sources = any(s.get("type") == "rag" for s in (sources or []))
            
            # If quality is low, attempt to improve
            # Lower threshold to 0.5 to reduce unnecessary improvements for RAG answers
            # Skip improvement if RAG sources are present (already well-sourced)
            if assessment["quality_score"] < 0.5 and not has_rag_sources:
                logger.info(f"Quality score {assessment['quality_score']} below threshold, improving answer...")
                improved_answer = await self._improve_answer(
                    question=question,
                    answer=answer,
                    issues=assessment.get("issues", []),
                    sources=sources
                )
                
                # Re-assess improved answer
                final_assessment = await self._assess_quality(question, improved_answer, sources)
                
                return {
                    "answer": improved_answer,
                    "sources": sources or [],
                    "quality_score": final_assessment["quality_score"],
                    "improvements_made": True,
                    "original_score": assessment["quality_score"],
                    "review_notes": final_assessment.get("strengths", [])
                }
            else:
                # Answer is good enough or has RAG sources
                if has_rag_sources:
                    logger.info(f"Skipping improvement for RAG-sourced answer (score: {assessment['quality_score']})")
                return {
                    "answer": answer,
                    "sources": sources or [],
                    "quality_score": assessment["quality_score"],
                    "improvements_made": False,
                    "review_notes": assessment.get("strengths", [])
                }
                
        except Exception as e:
            logger.error(f"Error in review: {str(e)}")
            # Return original answer if review fails
            return {
                "answer": answer,
                "sources": sources or [],
                "quality_score": 0.5,
                "improvements_made": False,
                "error": str(e)
            }
    
    async def _assess_quality(
        self,
        question: str,
        answer: str,
        sources: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Assess the quality of an answer
        """
        try:
            sources_summary = ""
            if sources:
                sources_summary = f"\n\nSources Available: {len(sources)} sources"
            
            assessment_prompt = f"""
You are a quality reviewer for technical support responses. Assess the following answer.

Question: {question}

Answer: {answer}
{sources_summary}

Evaluate the answer on these criteria:
1. Accuracy: Is the information correct?
2. Completeness: Does it fully address the question?
3. Clarity: Is it easy to understand?
4. Relevance: Does it stay on topic?
5. Helpfulness: Does it provide actionable information?

Respond with JSON in this format:
{{
    "quality_score": 0.0-1.0,
    "accuracy": 0.0-1.0,
    "completeness": 0.0-1.0,
    "clarity": 0.0-1.0,
    "relevance": 0.0-1.0,
    "helpfulness": 0.0-1.0,
    "strengths": ["list", "of", "strengths"],
    "issues": ["list", "of", "issues"]
}}
"""
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model=self.model_id,
                    contents=assessment_prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        response_mime_type="application/json"
                    )
                )
            )
            
            assessment = json.loads(response.text)
            logger.info(f"Quality assessment: score={assessment.get('quality_score', 0)}")
            
            return assessment
            
        except Exception as e:
            logger.error(f"Error assessing quality: {str(e)}")
            return {
                "quality_score": 0.5,
                "error": str(e)
            }
    
    async def _improve_answer(
        self,
        question: str,
        answer: str,
        issues: List[str],
        sources: List[Dict[str, Any]] = None
    ) -> str:
        """
        Improve an answer based on identified issues
        """
        try:
            issues_text = "\n- ".join(issues) if issues else "General improvement needed"
            
            sources_context = ""
            if sources:
                sources_context = "\n\nAvailable Sources:\n"
                for i, source in enumerate(sources[:3], 1):
                    sources_context += f"\n[{i}] {source.get('title', 'Source')}"
                    if source.get('url'):
                        sources_context += f" - {source['url']}"
                    sources_context += f"\n{source.get('content', '')[:300]}...\n"
            
            improvement_prompt = f"""
You are a technical support expert. Improve the following answer to address the identified issues.

Original Question: {question}

Current Answer: {answer}

Issues to Address:
- {issues_text}
{sources_context}

Provide an improved answer that:
1. Addresses all identified issues
2. Maintains or improves accuracy
3. Is clear and well-structured
4. Provides helpful, actionable information
5. Uses sources if available

Write only the improved answer, without meta-commentary.
"""
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model=self.model_id,
                    contents=improvement_prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.5,
                        max_output_tokens=1024
                    )
                )
            )
            
            improved = response.text.strip()
            logger.info("Answer improved successfully")
            return improved
            
        except Exception as e:
            logger.error(f"Error improving answer: {str(e)}")
            return answer  # Return original if improvement fails
