"""
NutriTrack MCP Server Configuration
"""

import os

# Backend API base URL
# Default: PythonAnywhere (online). Set NUTRITRACK_API_URL env var to override.
# For local development: export NUTRITRACK_API_URL=http://127.0.0.1:8000
API_BASE_URL = os.environ.get("NUTRITRACK_API_URL", "https://lichenxi.pythonanywhere.com")
