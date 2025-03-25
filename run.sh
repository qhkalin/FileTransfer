#!/bin/bash

# This script installs the requirements and runs the application

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
echo "Installing requirements..."
pip install -r app_requirements.txt

# Run the application
echo "Starting SecureFileVault application..."
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app