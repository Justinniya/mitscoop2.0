#!/bin/bash

VENV_DIR="env"
MAIN_APP="main.py"

if [ -n "$VIRTUAL_ENV" ]; then
    echo "Virtual environment already active."
    python "$MAIN_APP"
else
    echo "Virtual environment found."
    source "$VENV_DIR/Scripts/activate"
    python "$MAIN_APP"
fi

