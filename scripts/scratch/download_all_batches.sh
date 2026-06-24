#!/bin/bash

echo "Starting automated continuous batch downloads..."
while true; do
    echo "==============================================="
    echo "Starting next batch of 500 parts..."
    echo "==============================================="
    
    # Run the python script
    output=$(python batch_downloader.py download 500)
    
    # Print output to log
    echo "$output"
    
    # Check if there are no new parts left
    if echo "$output" | grep -q "All parts already downloaded!"; then
        echo "🎉 ALL PARTS HAVE BEEN SUCCESSFULLY DOWNLOADED!"
        break
    fi
    
    echo "Sleeping 5 seconds before starting the next batch..."
    sleep 5
done
