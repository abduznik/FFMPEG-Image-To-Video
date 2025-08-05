#!/bin/bash

# Start the X11 server in the background
termux-x11 :0 &

# Wait for the server to start
sleep 3

# Set the display variable and run the Python script
DISPLAY=:0 python app.py
