#!/bin/bash

# Function to run the curl command
run_curl() {
  curl http://127.0.0.1:5000/generate_recipe
}

# Loop to continuously run the curl command
while true; do
  run_curl
  # Adjust the sleep time (in seconds) as needed
  sleep 5
done