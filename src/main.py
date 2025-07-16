"""
Main program
"""

import json
import logging
import os
import sqlite3
from pathlib import Path

import yt_dlp as yt
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
loaded_env = load_dotenv()
if not loaded_env:
    raise EnvironmentError("Unable to load env vars from .env")


class Database:
    def __init__(self, db_path: str):
        """
        Connects to specified sqlite DB and creates tables for process if they don't
        already exist.
        """
        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(db_file)
        self.cursor = self.conn.cursor()
        self.setup_database()

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

    def setup_database(self):
        """
        Creates tables if not already present
        """
        self.create_table("channels", "id TEXT PRIMARY KEY, name TEXT, url TEXT")
        self.create_table(
            "videos",
            "id TEXT PRIMARY KEY, channelid TEXT NOT NULL, title TEXT, url TEXT",
        )
        self.create_table("transcripts", "id TEXT, language TEXT, transcript TEXT")


def refresh_channels(db: Database):
    """
    Goes through channels in the config file and adds any new channels to the database
    """
    for channel in os.environ["CHANNEL_LIST"].split(","):
        try:
            channel_info = yt.YoutubeDL({}).extract_info(
                channel, download=False, process=False
            )
        except Exception as e:
            logger.error(f"Error getting channel info for {channel}: {e}")
            continue

        if not channel_info:
            # TODO handle more elegantly, placeholder
            exit(1)

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
        try:
            videos = db.select("videos", "id", "channelid = ?", (channel_id,))
        except Exception as e:
            logger.error(f"Error getting videos for {channel_id}: {e}")
            continue

        # Create temp txt file with video IDs for yt-dlp to read
        with open("temp.txt", "w") as f:
            for video in videos:
                f.write(f"{video[0]}\n")

        # Download the info for the videos that are not in the download archive
        # TODO Handle download archive to avoid hitting same videos repeatedly
        with yt.YoutubeDL(
            params={
                "skip_download": True,
                "extract_flat": False,
                "flat_playlist": False,
                "ignoreerrors": True,
                "quiet": True,
                "no_warnings": True,
                "outtmpl": "dummy",
            }
        ) as ydl:
            try:
                info_dict = ydl.extract_info(channel_url, download=False)
            except Exception as e:
                logger.error(f"Error getting video info for {channel_id}: {e}")
                continue

        if "entries" in info_dict:
            # Add videos to the database if not already present
            for video in info_dict["entries"]:
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
                        logger.error(f"Error adding video to database: {e}")


def download_transcripts(db: Database):
    """
    Downloads transcripts for all videos in the database if not already present
    Checks 'videos' table for entries with no corresponding entry in 'transcripts' table.
    For any that do not have an entry, check for an english transcript and
    try to donwload it.
    """
    ytdl_opts = config["ytdl_options"]
    ytdl_opts["write_auto_sub"] = True
    ytdl_opts["skip_download"] = True

    for result in db.query(
        "SELECT id, url FROM videos WHERE id NOT IN (SELECT id FROM transcripts)"
    ):
        video_id = result[0]
        video_url = result[1]
        ytdl_opts["outtmpl"] = f"{video_id}.%(ext)s"
        with yt.YoutubeDL(ytdl_opts) as ydl:
            try:
                video_info = ydl.extract_info(video_url)
                if "automatic_captions" in video_info:
                    for lang in video_info["automatic_captions"]:
                        if lang != "en":
                            continue
                        # json3 format is first element in list
                        transcript_url = video_info["automatic_captions"][lang][0][
                            "url"
                        ]
                        # Download the data from URL
                        transcript = ydl.urlopen(transcript_url).read().decode("utf-8")
                        db.insert(
                            "transcripts",
                            "id, language, transcript",
                            (video_id, lang, transcript),
                        )

            except Exception as e:
                logger.error(f"Error getting transcript for {video_id}: {e}")
                continue


if __name__ == "__main__":
    """
    Main function
    """
    # Create database object
    db = Database(os.environ["YT_DB_DIR"])

    refresh_channels(db)
    refresh_videos(db)
    download_transcripts(db)
    db.close()
