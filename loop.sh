#!/bin/bash

# Replace YOUR_PORT_NUMBER with the actual port number (e.g., 5000)
PORT=5000

# Function to run the curl command
run_curl() {
	curl http://0.0.0.0:$PORT/generate_recipe
}

# Loop to continuously run the curl command
while true; do
	run_curl
	# Adjust the sleep time (in seconds) as needed
	sleep 5
done
