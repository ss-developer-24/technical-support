import streamlit as st
import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Technical Support Assistant",
    page_icon="🤖",
    layout="centered"
)

# Initialize session state for API host
if "api_host" not in st.session_state:
    st.session_state.api_host = os.environ.get("API_HOST", "http://localhost:8000")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Title
st.title("🤖 Technical Support Assistant")

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    api_host = st.text_input(
        "Backend API Host",
        value=st.session_state.api_host,
        help="Enter the backend API URL (e.g., http://localhost:8000 or https://api.example.com)"
    )
    
    if api_host != st.session_state.api_host:
        st.session_state.api_host = api_host
        st.success("API host updated!")
    
    st.divider()
    
    # Clear chat button
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.rerun()
    
    st.divider()
    
    # Connection status
    st.subheader("Connection Status")
    try:
        response = requests.get(f"{st.session_state.api_host}/health", timeout=5)
        if response.status_code == 200:
            st.success("✅ Connected")
        else:
            st.error("❌ Backend unavailable")
    except Exception as e:
        st.error(f"❌ Connection failed")
        st.caption(f"Error: {str(e)}")
    
    st.divider()
    
    # Document ingestion section
    st.subheader("📚 Document Management")
    st.caption("Ingest PDFs from GCS bucket into RAG system")
    
    if st.button("🔄 Ingest Documents", use_container_width=True):
        with st.spinner("Starting document ingestion..."):
            try:
                ingest_response = requests.post(
                    f"{st.session_state.api_host}/api/ingest",
                    timeout=10  # Short timeout since it returns immediately
                )
                
                if ingest_response.status_code == 200:
                    result = ingest_response.json()
                    st.success(f"✅ {result.get('message', 'Ingestion started')}")
                    st.info("📝 Check backend logs for ingestion progress and completion status.")
                else:
                    st.error(f"❌ Ingestion failed: {ingest_response.status_code}")
                    
            except requests.exceptions.Timeout:
                st.error("⚠️ Request timed out.")
            except requests.exceptions.ConnectionError:
                st.error(f"⚠️ Could not connect to backend")
            except Exception as e:
                st.error(f"⚠️ Error: {str(e)}")

# Main chat interface
st.divider()

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Display sources for assistant messages
        if message["role"] == "assistant" and message.get("sources"):
            sources = message["sources"]
            st.divider()
            st.markdown("**📚 Sources:**")
            
            # Separate RAG and web sources
            rag_sources = [s for s in sources if s.get("type") == "rag"]
            web_sources = [s for s in sources if s.get("type") == "web"]
            
            # Display RAG sources (internal documentation)
            if rag_sources:
                st.markdown("*Internal Documentation:*")
                for i, source in enumerate(rag_sources, 1):
                    with st.expander(f"📄 {source.get('document', 'Document')} (Relevance: {source.get('score', 0):.2f})"):
                        st.markdown(f"**Source:** {source.get('source', 'Unknown')}")
                        st.markdown(f"**Excerpt:** {source.get('content', 'N/A')}")
            
            # Display web sources
            if web_sources:
                if rag_sources:
                    st.markdown("")
                st.markdown("*Web Sources:*")
                for i, source in enumerate(web_sources, 1):
                    with st.expander(f"🌐 {source.get('title', 'Web Source')} (Relevance: {source.get('score', 0):.2f})"):
                        st.markdown(f"**URL:** [{source.get('url', 'N/A')}]({source.get('url', '#')})")
                        st.markdown(f"**Excerpt:** {source.get('content', 'N/A')}")

# Chat input
if question := st.chat_input("Enter your question here..."):
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": question, "sources": []})
    
    with st.chat_message("user"):
        st.markdown(question)
    
    # Get response from backend
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # Make API request to backend
                response = requests.post(
                    f"{st.session_state.api_host}/api/question",
                    json={"question": question},
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    answer = result.get("answer", "No response received")
                    sources = result.get("sources", [])
                    
                    # Display answer
                    st.markdown(answer)
                    
                    # Display sources if available
                    if sources:
                        st.divider()
                        st.markdown("**📚 Sources:**")
                        
                        # Separate RAG and web sources
                        rag_sources = [s for s in sources if s.get("type") == "rag"]
                        web_sources = [s for s in sources if s.get("type") == "web"]
                        
                        # Display RAG sources (internal documentation)
                        if rag_sources:
                            st.markdown("*Internal Documentation:*")
                            for i, source in enumerate(rag_sources, 1):
                                with st.expander(f"📄 {source.get('document', 'Document')} (Relevance: {source.get('score', 0):.2f})"):
                                    st.markdown(f"**Source:** {source.get('source', 'Unknown')}")
                                    st.markdown(f"**Excerpt:** {source.get('content', 'N/A')}")
                        
                        # Display web sources
                        if web_sources:
                            if rag_sources:
                                st.markdown("")
                            st.markdown("*Web Sources:*")
                            for i, source in enumerate(web_sources, 1):
                                with st.expander(f"🌐 {source.get('title', 'Web Source')} (Relevance: {source.get('score', 0):.2f})"):
                                    st.markdown(f"**URL:** [{source.get('url', 'N/A')}]({source.get('url', '#')})")  
                                    st.markdown(f"**Excerpt:** {source.get('content', 'N/A')}")
                    
                    st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources})
                else:
                    error_msg = f"Error: Backend returned status code {response.status_code}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg, "sources": []})
                    
            except requests.exceptions.Timeout:
                error_msg = "⚠️ Request timed out. Please try again."
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg, "sources": []})
                
            except requests.exceptions.ConnectionError:
                error_msg = f"⚠️ Could not connect to backend at {st.session_state.api_host}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg, "sources": []})
                
            except Exception as e:
                error_msg = f"⚠️ An error occurred: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg, "sources": []})

# Footer
st.divider()
st.caption("(c) 2026 Technical Support Assistant. All rights reserved.")
