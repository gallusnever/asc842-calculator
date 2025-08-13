#!/bin/bash

# ASC 842 Calculator - Quick Start Script

echo "🚀 Starting ASC 842 Lease Calculator..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "✅ Activating virtual environment..."
source venv/bin/activate

# Check if requirements are installed
if ! python -c "import flask" 2>/dev/null; then
    echo "📚 Installing dependencies..."
    pip install -r requirements.txt
fi

# Start the application
echo ""
echo "🎯 Starting Flask application..."
echo "📊 ASC 842 Calculator will be available at: http://localhost:5000"
echo "📝 Press Ctrl+C to stop the server"
echo ""

python app.py
