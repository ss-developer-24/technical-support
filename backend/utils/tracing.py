"""
LangSmith observability and tracing utilities
"""
import os
import logging
from functools import wraps
from typing import Any, Dict, Optional, Callable

logger = logging.getLogger(__name__)

# LangSmith configuration - Set environment variables for LangSmith SDK
LANGSMITH_ENABLED = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "technical-support")

# Set LangSmith environment variables if enabled
if LANGSMITH_ENABLED and LANGSMITH_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = LANGSMITH_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = LANGSMITH_PROJECT
    logger.info(f"✅ LangSmith tracing enabled for project: {LANGSMITH_PROJECT}")
else:
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    logger.info("⚠️ LangSmith tracing disabled - LANGSMITH_TRACING={}, API_KEY set={}".format(
        os.getenv("LANGSMITH_TRACING"), bool(LANGSMITH_API_KEY)))

# Initialize LangSmith client if enabled
langsmith_client = None
if LANGSMITH_ENABLED and LANGSMITH_API_KEY:
    try:
        from langsmith import Client
        langsmith_client = Client(api_key=LANGSMITH_API_KEY)
        logger.info(f"📊 LangSmith client initialized successfully")
    except ImportError:
        logger.warning("⚠️ langsmith package not installed")
        LANGSMITH_ENABLED = False
    except Exception as e:
        logger.error(f"❌ Failed to initialize LangSmith client: {str(e)}")
        LANGSMITH_ENABLED = False


def trace_agent(agent_name: str, run_type: str = "chain"):
    """
    Decorator to trace agent function calls with LangSmith
    
    Args:
        agent_name: Name of the agent (e.g., "orchestrator", "researcher")
        run_type: Type of run ("chain", "llm", "tool", "retriever")
    """
    def decorator(func: Callable):
        if not LANGSMITH_ENABLED:
            # If tracing disabled, return function as-is
            logger.debug(f"Tracing disabled for {agent_name}.{func.__name__}")
            return func
        
        try:
            from langsmith import traceable
            
            # Apply traceable decorator directly
            traced_func = traceable(
                name=f"{agent_name}.{func.__name__}",
                run_type=run_type,
            )(func)
            
            logger.info(f"🔍 Enabled tracing for: {agent_name}.{func.__name__}")
            return traced_func
            
        except ImportError:
            logger.warning(f"⚠️ langsmith not available for {agent_name}.{func.__name__}")
            return func
        except Exception as e:
            logger.warning(f"⚠️ Failed to trace {agent_name}.{func.__name__}: {str(e)}")
            return func
    
    return decorator


def log_interaction(
    question: str,
    answer: str,
    sources: Optional[list] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Log a user interaction to LangSmith
    
    Args:
        question: User's question
        answer: Agent's answer
        sources: List of sources used
        metadata: Additional metadata
    """
    if not LANGSMITH_ENABLED or not langsmith_client:
        return
    
    try:
        logger.debug(f"📝 Logging interaction to LangSmith: {question[:50]}...")
    except Exception as e:
        logger.debug(f"Failed to log interaction: {str(e)}")


def get_langsmith_info() -> Dict[str, Any]:
    """
    Get LangSmith configuration information
    
    Returns:
        Dict with LangSmith status and configuration
    """
    return {
        "enabled": LANGSMITH_ENABLED,
        "project": LANGSMITH_PROJECT if LANGSMITH_ENABLED else None,
        "api_key_set": bool(LANGSMITH_API_KEY),
        "client_initialized": langsmith_client is not None
    }


class LangSmithTracer:
    """Context manager for manual tracing (not currently used)"""
    pass
