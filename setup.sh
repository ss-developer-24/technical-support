#!/bin/bash
# Quick setup script for local development

set -e

echo "🚀 Technical Support Assistant - Setup Script"
echo "=============================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $python_version"

# Setup backend
echo ""
echo "📦 Setting up backend..."
cd backend

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing backend dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Edit backend/.env with your API keys:"
    echo "   - GOOGLE_API_KEY"
    echo "   - TAVILY_API_KEY"
    echo "   - GCP_PROJECT_ID"
    echo "   - GCS_BUCKET_NAME"
    echo ""
fi

cd ..

# Setup frontend
echo ""
echo "📦 Setting up frontend..."
cd frontend
pip install -q -r requirements.txt

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "✅ Created frontend/.env (using default: http://localhost:8000)"
fi

cd ..

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit backend/.env with your API keys"
echo "2. Edit frontend/.env to set backend URL (default: http://localhost:8000)"
echo "3. Upload PDF documents to your GCS bucket"
echo "4. Run backend: cd backend && python main.py"
echo "5. Run frontend: cd frontend && streamlit run app.py"
echo ""
echo "For detailed instructions, see:"
echo "- backend/README.md (backend setup)"
echo "- frontend/README.md (frontend setup)"
echo "- README.md (overview)"
