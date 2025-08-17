#!/bin/bash

cd frontend

if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

echo "Starting PosterGen WebUI frontend..."
echo "Frontend will be available at: http://localhost:3000"
echo ""

npm run dev