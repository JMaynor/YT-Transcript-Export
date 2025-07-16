"""
Main program
"""

import atexit
import os
import sqlite3
from pathlib import Path

import yt_dlp as yt
from dotenv import load_dotenv

from .logger import AppriseNotifier, error_handler, logger

loaded_env = load_dotenv()
if not loaded_env:
    raise EnvironmentError("Unable to load env vars from .env")


@atexit.register
def send_error_summary():
    """
    Send out a summary of any errors that occurred during
    program run to defined apprise endpoints.
    """
    errors = error_handler.get_errors()
    if errors:
        error_summary = "\n".join(errors)
        AppriseNotifier().error_notify(
            f"Program exited with the following errors:\n{error_summary}"
        )


class Database:
    """
    The Database class handles connecting to and working with the sqlite db file
    for this project.
    """

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

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def create_table(self, table_name: str, columns: str):
        self.cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({columns})")
        self.conn.commit()

    def insert(self, table_name: str, columns: str, values):
        placeholders = ", ".join("?" * len(values))
        self.cursor.execute(
            f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})", values
        )
        self.conn.commit()

    def select(self, table_name: str, columns: str, condition: str, params: tuple):
        self.cursor.execute(
            f"SELECT {columns} FROM {table_name} WHERE {condition}", params
        )
        return self.cursor.fetchall()

    def query(self, query: str):
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
    logger.info("Refreshing channels.")

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
    Goes through channels in the config file and adds any new videos to the database.
    This is a two-step process to improve performance:
    1. Quickly fetch a list of all video IDs from the channel.
    2. Get detailed information for only the videos that are not already in the DB.
    """
    logger.info("Refreshing videos.")

    # For each channel in database
    channels = db.select("channels", "id, url", "1", ())
    for channel in channels:
        channel_id = channel[0]
        channel_url = channel[1]
        # Get IDs of videos already in the database for this channel
        try:
            videos = db.select("videos", "id", "channelid = ?", (channel_id,))
            existing_video_ids = {video[0] for video in videos}
        except Exception as e:
            logger.error(f"Error getting existing videos for {channel_id}: {e}")
            continue

        # Step 1: Get a flat list of all video IDs from the channel (this is fast)
        try:
            with yt.YoutubeDL(
                {"extract_flat": True, "quiet": True, "ignoreerrors": True}
            ) as ydl:
                playlist_dict = ydl.extract_info(
                    channel_url + "/videos", download=False
                )
                if not playlist_dict or "entries" not in playlist_dict:
                    logger.warning(f"Could not retrieve video list for {channel_id}")
                    continue
                all_video_ids = {entry["id"] for entry in playlist_dict["entries"]}
        except Exception as e:
            logger.error(f"Error getting flat video list for {channel_id}: {e}")
            continue

        # Step 2: Determine which video IDs are new
        new_video_ids = all_video_ids - existing_video_ids

        if not new_video_ids:
            logger.info(f"No new videos found for channel {channel_id}")
            continue

        logger.info(f"Found {len(new_video_ids)} new videos for channel {channel_id}")

        # Step 3: Get full information for only the new videos
        new_video_urls = [
            f"https://www.youtube.com/watch?v={id}" for id in new_video_ids
        ]

        with yt.YoutubeDL(
            {
                "skip_download": True,
                "quiet": True,
                "no_warnings": True,
                "outtmpl": "dummy",
                "ignoreerrors": True,
            }
        ) as ydl:
            try:
                # ydl.extract_info with a list of URLs returns an iterator of video info dicts
                video_info_iterator = ydl.extract_info(new_video_urls, download=False)
                if video_info_iterator:
                    for video in video_info_iterator:
                        if video and isinstance(video, dict):
                            try:
                                db.insert(
                                    "videos",
                                    "id, channelid, title, url",
                                    (
                                        video.get("id"),
                                        channel_id,
                                        video.get("title"),
                                        video.get("url"),
                                    ),
                                )
                            except Exception as e:
                                logger.error(
                                    f"Error adding video {video.get('id')} to database: {e}"
                                )
            except Exception as e:
                logger.error(
                    f"Error getting video info for new videos in {channel_id}: {e}"
                )
                continue


def download_transcripts(db: Database):
    """
    Downloads transcripts for all videos in the database if not already present
    Checks 'videos' table for entries with no corresponding entry in 'transcripts' table.
    For any that do not have an entry, check for an english transcript and
    try to donwload it.
    """

    logger.info("Downloading transcripts.")

    for result in db.query(
        "SELECT id, url FROM videos WHERE id NOT IN (SELECT id FROM transcripts)"
    ):
        video_id = result[0]
        video_url = result[1]
        logger.info(f"Downloading transcript for video id {video_id}")
        with yt.YoutubeDL(
            params={
                "skip_download": True,
                "extract_flat": False,
                "flat_playlist": False,
                "ignoreerrors": True,
                "quiet": True,
                "no_warnings": True,
                "outtmpl": "dummy",
                "write_auto_sub": True,
            }
        ) as ydl:
            try:
                video_info = ydl.extract_info(video_url)

                if not video_info:
                    exit(1)

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
    with Database(os.environ["YT_DB_DIR"]) as db:
        refresh_channels(db)
        refresh_videos(db)
        download_transcripts(db)
