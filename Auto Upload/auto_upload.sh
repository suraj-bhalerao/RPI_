#!/bin/bash
 
# Path to your Python script

PYTHON_SCRIPT="/home/sharukh/CIAP/one.py"
 
# SSID of the home network

HOME_SSID="AEPL-R&D"
 
# Check the current SSID

CURRENT_SSID=$(iwgetid -r)
 
# If connected to the home network, run the Python script

if [ "$CURRENT_SSID" == "$HOME_SSID" ]; then

    python3 "$PYTHON_SCRIPT"

fi

 
