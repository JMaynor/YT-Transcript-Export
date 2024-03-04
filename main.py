"""
Main program
"""

import json
import os
import sqlite3

import apprise
import yt_dlp as yt

# Import JSON config file
try:
    with open("config.json") as json_file:
        config = json.load(json_file)
except:
    print("Error reading config file")
    exit(1)

apobj = apprise.Apprise()
[apobj.add(x) for x in config["apprise_endpoints"] if "apprise_endpoints" in config]


class Database:
    def __init__(self, db_name):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()

    def create_table(self, table_name, columns):
        self.cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({columns})")
        self.conn.commit()

    def insert(self, table_name, columns, values):
        placeholders = ", ".join("?" * len(values))
        self.cursor.execute(
            f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})", values
        )
        self.conn.commit()

    def select(self, table_name, columns, condition, params):
        self.cursor.execute(
            f"SELECT {columns} FROM {table_name} WHERE {condition}", params
        )
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


def refresh_channels(db: Database):
    """
    Goes through channels in the config file and adds any new channels to the database
    """
    for channel in config["channels"]:
        try:
            channel_info = yt.YoutubeDL({}).extract_info(
                channel, download=False, process=False
            )
        except Exception as e:
            print(f"Error getting channel info for {channel}: {e}")
            continue

        # Add channel to database if not present
        if not db.select("channels", "id", "id = ?", (channel_info["id"],)):
            db.insert(
                "channels",
                "id, name, url",
                (
                    channel_info["id"],
                    channel_info["channel"],
                    channel_info["channel_url"],
                ),
            )


def refresh_videos(db: Database):
    """
    Goes through channels in the config file and adds any new videos to the database
    """
    # For each channel in database
    channels = db.select("channels", "id, url", "1", ())
    for channel in channels:
        channel_id = channel[0]
        channel_url = channel[1]
        # Get videos already in DB for channel
        videos = db.select("videos", "id", "channelid = ?", (channel_id,))

        # Create temp txt file with video IDs for yt-dlp to read
        with open("temp.txt", "w") as f:
            for video in videos:
                f.write(f"{video[0]}\n")

        ytdl_opts = config["ytdl_options"]
        ytdl_opts["download_archive"] = "temp.txt"

        # Download the info for the videos that are not in the download archive
        with yt.YoutubeDL(ytdl_opts) as ydl:
            try:
                info_dict = ydl.extract_info(channel_url, download=False)
            except Exception as e:
                print(f"Error getting video info for {channel_id}: {e}")
                continue

        os.remove("temp.txt")

        # Get the list of videos from the info dict
        videos = info_dict["entries"]

        # Add videos to the database if not already present
        for video in videos:
            # Add video to database if not present
            if not db.select("videos", "id", "id = ?", (video["id"],)):
                try:
                    db.insert(
                        "videos",
                        "id, channelid, title, url",
                        (
                            video["id"],
                            channel_id,
                            video["title"],
                            video["webpage_url"],
                        ),
                    )
                except Exception as e:
                    print(f"Error adding video to database: {e}")


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

    refresh_channels(db)

    refresh_videos(db)

    # download_transcripts(db)

    db.close()
