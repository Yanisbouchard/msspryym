#!/bin/bash

while true; do
    python3 app.py >> app.log 2>&1
    echo "Server stopped, restarting in 5 seconds..." >> app.log
    sleep 5
done
