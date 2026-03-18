#!/bin/bash
clear
echo "  MultimediaTrack — Iniciando..."
cd "$(dirname "$0")"
echo "  Directorio: $(pwd)"
pip3 install flask pandas openpyxl groq --quiet
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
    echo "  API Key cargada"
fi
(sleep 2 && open "http://127.0.0.1:5000") &
python3 app.py
