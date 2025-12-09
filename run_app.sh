#!/bin/bash
# Script to run the JATS XML Transformer App

# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate the virtual environment and run the app
"$DIR/.venv/bin/streamlit" run "$DIR/streamlit_app.py"
