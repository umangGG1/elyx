#!/bin/bash
# Start the health activity scheduler web interface

echo "=================================="
echo "Health Activity Scheduler Web UI"
echo "=================================="
echo ""

# Check if scheduler has been run
if [ ! -f "output/results/schedule.json" ]; then
    echo "⚠️  No schedule data found. Running scheduler first..."
    echo ""
    venv/bin/python3 run_scheduler.py
    echo ""
fi

echo "🚀 Starting web server..."
echo "📊 Open your browser to: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=================================="
echo ""

venv/bin/python3 web_app.py
