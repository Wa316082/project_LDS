#!/bin/bash

echo "===================================="
echo "Legal Document Analyzer Setup"
echo "===================================="
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8+ from https://python.org"
    exit 1
fi

echo "Python found. Proceeding with setup..."
echo

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to create virtual environment"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "Installing required packages..."
pip install --upgrade pip
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install requirements"
    exit 1
fi

# Install spaCy model
echo "Installing spaCy English model..."
python -m spacy download en_core_web_sm

if [ $? -ne 0 ]; then
    echo "WARNING: Failed to install spaCy model. You may need to install it manually."
fi

echo
echo "===================================="
echo "Setup completed successfully!"
echo "===================================="
echo
echo "Next steps:"
echo "1. Configure Firebase in firebase_setup.py"
echo "2. Update cookie password in cookie_manager.py"
echo "3. Run: streamlit run main.py"
echo
echo "To activate the virtual environment in future sessions:"
echo "source venv/bin/activate"
echo

read -p "Press any key to continue..."
