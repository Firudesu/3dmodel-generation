#!/usr/bin/env python3
"""
Simple start script that just works for testing
"""
import os

# Create directories
os.makedirs('uploads', exist_ok=True)
os.makedirs('output', exist_ok=True)
print("✅ Directories created")

# Import and run the Flask app directly
from app import app

# Get port from Render
port = int(os.environ.get('PORT', 10000))
print(f"🚀 Starting Flask app on port {port}")

# Run Flask directly (fine for testing)
app.run(host='0.0.0.0', port=port, debug=False)