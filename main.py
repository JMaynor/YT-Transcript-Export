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


class Database:
    def __init__(self, db_name):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()

    def create_table(self, table_name, columns):
        self.cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({columns})")
        self.conn.commit()

    def insert(self, table_name, columns, values):
        self.cursor.execute(f"INSERT INTO {table_name} ({columns}) VALUES ({values})")
        self.conn.commit()

    def select(self, table_name, columns, condition):
        self.cursor.execute(f"SELECT {columns} FROM {table_name} WHERE {condition}")
        return self.cursor.fetchall()

    def close(self):
        self.conn.close()


def setup_database(db: Database):
    """
    Creates tables if not already present
    """
    # Check if channels table exists, if not create it
    db.create_table("channels", "id TEXT PRIMARY KEY, name TEXT")

    # Check if videos table exists, if not create it
    db.create_table(
        "videos", "id TEXT PRIMARY KEY, channelid TEXT NOT NULL, title TEXT, url TEXT"
    )

    # Check if transcripts table exists, if not create it
    db.create_table("transcripts", "id TEXT PRIMARY KEY, transcript TEXT")


def refresh_videos(db: Database):
    """
    Goes through channels in the config file and adds any new videos to the database
    """
    for channel in config["channels"]:
        # Get channel ID
        channel_id = yt.YoutubeDL({}).extract_info(channel, download=False)["id"]

        # Add channel to database if not present
        if not db.select("channels", "id", f"id = '{channel_id}'"):
            db.insert("channels", "id, name", f"'{channel_id}', '{channel}'")

        # Get all videos from the channel
        videos = yt.YoutubeDL({}).extract_info(channel, download=False)["entries"]

        # Add videos to the database if not already present
        for video in videos:
            # Get video ID
            video_id = video["id"]

            # Add video to database if not present
            if not db.select("videos", "id", f"id = '{video_id}'"):
                db.insert(
                    "videos",
                    "id, channelid, title, url",
                    f"'{video_id}', '{channel_id}', '{video['title']}', '{video['webpage_url']}'",
                )


if __name__ == "__main__":
    """
    Main function
    """
    # Create database object
    db = Database(config["database"])

    setup_database(db)

    refresh_videos(db)

    db.close()
