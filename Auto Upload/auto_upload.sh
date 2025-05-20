#!/bin/bash
PYTHON_SCRIPT="/home/sharukh/CIAP/one.py"
HOME_SSID="AEPL-R&D"
CURRENT_SSID=$(iwgetid -r)
if [ "$CURRENT_SSID" == "$HOME_SSID" ]; then
    python3 "$PYTHON_SCRIPT"
fi