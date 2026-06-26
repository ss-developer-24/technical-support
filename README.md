# Technical Support Assistant

A full-stack technical support application with a Streamlit frontend and a FastAPI backend powered by Google ADK agents. The system uses three specialized agents (Orchestrator, Researcher, and Reviewer) to provide intelligent, researched, and quality-controlled responses.

## 🤖 Architecture

### Backend (FastAPI + Google ADK)
- **Orchestrator Agent**: Coordinates workflow between agents using Gemini
- **Researcher Agent**: 
  - Web search capability via Tavily API
  - RAG-enabled retrieval using Vertex AI embeddings
  - Reads PDF documents from Google Cloud Storage
- **Reviewer Agent**: Validates and improves response quality

### Frontend (Streamlit)
- Intuitive chat interface for user interactions
- Real-time connection monitoring
- Configurable backend endpoint

## 🚀 Quick Start

**New to the project?** See [GETTING_STARTED.md](GETTING_STARTED.md) for a complete setup guide or [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for common commands.

### Backend Setup

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys and GCP settings

# Run the backend
python main.py
```

Backend runs at `http://localhost:8000`

**See [backend/README.md](backend/README.md) for complete setup instructions.**

### Frontend Setup

```bash
cd frontend

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env to set API_HOST (default: http://localhost:8000)

# Run the application
streamlit run app.py
```

Frontend runs at `http://localhost:8501`

**See [frontend/README.md](frontend/README.md) for complete setup instructions.**

## 🐳 Docker Deployment

### Build and Run Backend

```bash
cd backend

# Build
docker build -t technical-support-backend .

# Run with environment variables
docker run -p 8000:8000 \
  -e GOOGLE_API_KEY=your-key \
  -e TAVILY_API_KEY=your-key \
  -e GCP_PROJECT_ID=your-project \
  -e GCS_BUCKET_NAME=your-bucket \
  technical-support-backend
```

### Build and Run Frontend

```bash
cd frontend

# Build
docker build -t technical-support-frontend .

# Run with local backend
docker run -p 8080:8080 -e API_HOST=http://host.docker.internal:8000 technical-support-frontend

# Run with production backend
docker run -p 8080:8080 -e API_HOST=https://technical-support-backend-255507724672.us-central1.run.app technical-support-frontend
```

Access at `http://localhost:8080`

## ☁️ Google Cloud Run Deployment

### Deployed Services
**Backend URL:** https://technical-support-backend-255507724672.us-central1.run.app  
**Frontend URL:** https://technical-support-frontend-255507724672.us-central1.run.app  
**Status:** ✅ Both services deployed and running  
**Region:** us-central1

### Deploy Backend

```bash
cd backend
./deploy.sh
```

See [backend/README.md](backend/README.md) for detailed deployment instructions.

### Deploy Frontend

**Option 1: Using Cloud Build (recommended)**

```bash
cd frontend
gcloud builds submit --config cloudbuild.yaml
```

This will automatically build, push, and deploy to Cloud Run with the backend URL configured.

**Option 2: Using the deployment script**
```bash
cd frontend
./deploy.sh technical-support-499903 us-central1 https://technical-support-backend-255507724672.us-central1.run.app
```

## 📁 Project Structure

```
technical-support/
├── backend/                    # FastAPI backend with Google ADK agents
│   ├── agents/                # Agent implementations
│   │   ├── orchestrator.py   # Orchestrator agent
│   │   ├── researcher.py     # Researcher with Tavily & RAG
│   │   ├── reviewer.py       # Response quality reviewer
│   │   └── rag_engine.py     # Vertex AI RAG engine
│   ├── main.py               # FastAPI application
│   ├── requirements.txt      # Backend dependencies
│   ├── Dockerfile            # Backend container
│   ├── deploy.sh             # Backend deployment script
│   ├── cloudbuild.yaml       # Backend Cloud Build config
│   └── README.md             # Backend documentation
├── frontend/                  # Streamlit frontend
│   ├── app.py                # Main Streamlit application
│   ├── requirements.txt      # Frontend dependencies
│   ├── Dockerfile            # Frontend container
│   ├── deploy.sh             # Frontend deployment script
│   ├── cloudbuild.yaml       # Frontend Cloud Build config
│   └── README.md             # Frontend documentation
├── setup.sh                   # Automated setup script
└── README.md                  # This file
```

## 🔑 Required API Keys

1. **Google AI API Key** - For Gemini models
   - Get from: https://aistudio.google.com/app/apikey
   
2. **Tavily API Key** - For web search
   - Get from: https://tavily.com/

3. **Google Cloud Project** - For Vertex AI and Cloud Storage
   - Create at: https://console.cloud.google.com/

## 📚 Documentation

- **[GETTING_STARTED.md](GETTING_STARTED.md)** - Complete setup guide for beginners
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Common commands and quick reference
- **[backend/README.md](backend/README.md)** - Backend setup & deployment
- **[frontend/README.md](frontend/README.md)** - Frontend setup & deployment
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture and design
- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Comprehensive project overview
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Deployment guide

## 🔌 Backend API Endpoints

The backend provides these endpoints:

- `GET /health` - Health check and agent status
- `POST /api/question` - Process user questions through agents
- `GET /api/status` - System configuration and status
- `POST /api/ingest` - Ingest PDF documents for RAG

## 🌟 Features

### Agent System
- **Multi-agent collaboration** using Google ADK
- **Intelligent routing** via Orchestrator
- **Web search integration** with Tavily
- **RAG retrieval** from PDF documents using Vertex AI
- **Quality assurance** through automated review

### User Interface
- Clean chat-based interface
- Real-time backend health monitoring
- Conversation history
- Configurable API endpoint
- Error handling and timeouts

### Cloud Native
- Containerized microservices
- Google Cloud Run deployment
- Scalable architecture
- Secret management with Secret Manager
- Cloud Build CI/CD pipelines

## 🧪 Testing

```bash
# Test backend
cd backend && python test_backend.py

# Test with curl
curl http://localhost:8000/health

# Ask a question
curl -X POST http://localhost:8000/api/question \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Python?"}'
```

## 🔧 Configuration

Set the `API_HOST` environment variable to point to your backend API:

```bash
export API_HOST=https://your-backend-api.com
```

Or configure it through the UI sidebar.

## 📖 Learn More

- [Google ADK Documentation](https://ai.google.dev/gemini-api/docs/adk)
- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [Tavily API Documentation](https://docs.tavily.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)

## 🚀 Ready to Deploy?

1. Complete the [GETTING_STARTED.md](GETTING_STARTED.md) guide
2. Review [ARCHITECTURE.md](ARCHITECTURE.md) to understand the system
3. Follow [backend/README.md](backend/README.md) for deployment
4. Use [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for common commands

---

Built with ❤️ using Google ADK, Vertex AI, and Tavily
