#!/usr/bin/env python3
"""
Simple script to run the FastAPI server for the Berlinger Fridge Tag API.
"""

import uvicorn
from api import app

if __name__ == "__main__":
    print("Starting Berlinger Fridge Tag API server...")
    print("API will be available at: http://localhost:8000")
    print("Interactive docs at: http://localhost:8000/docs")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)