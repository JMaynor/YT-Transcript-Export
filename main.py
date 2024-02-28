"""
Main program
"""

import json
import sqlite3

import yt_dlp as yt

# Import JSON config file
try:
    with open("config.json") as json_file:
        config = json.load(json_file)
except:
    print("Error reading config file")
    exit(1)

if __name__ == "__main__":
    print()
