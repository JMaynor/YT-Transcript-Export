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

    def query(self, query):
        self.cursor.execute(query)
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
    db.create_table(
        "transcripts", "id TEXT, language TEXT, transcript TEXT, raw_transcript BLOB"
    )


def refresh_videos(db: Database):
    """
    Goes through channels in the config file and adds any new videos to the database
    """
    for channel in config["channels"]:
        # Get channel ID
        try:
            channel_info = yt.YoutubeDL({}).extract_info(channel, download=False, process=False)
        except Exception as e:
            print(f"Error getting channel info for {channel}: {e}")
            continue

        # Add channel to database if not present
        if not db.select("channels", "id", f"id = '{channel_info['id']}'"):
            db.insert(
                "channels",
                "id, name",
                f"'{channel_info['id']}', '{channel_info['channel']}'",
            )

        # Add videos to the database if not already present
        # TODO: Change strategy here. Don't want to have to go through all videos every time
        # Would be better to only pull video info that is not already in the database. Would
        # be far faster on subsequent runs.
        for video in channel_info["entries"]:
            # Add video to database if not present
            if not db.select("videos", "id", f"id = '{video["id"]}'"):
                db.insert(
                    "videos",
                    "id, channelid, title, url",
                    f"'{video["id"]}', '{channel_info['id']}', '{video['title']}', '{video['webpage_url']}'",
                )


def download_transcripts(db: Database):
    """
    Downloads transcripts for all videos in the database if not already present
    Checks 'videos' table for entries with no corresponding entry in 'transcripts' table.
    """
    for video in db.query(""):
        print()


if __name__ == "__main__":
    """
    Main function
    """
    # Create database object
    db = Database(config["database"])

    setup_database(db)

    refresh_videos(db)

    download_transcripts(db)

    db.close()
