# YT-Transcript-Export

Exports transcripts from a YT channel and ingests into some database for later searching. Perhaps sqlite, has support for JSON and JSON would be useful for later using the ingested data.

Script has several steps.

First, checks for new videos from the channels in the config file and downloads them if they are not already present into the 'transcripts' folder.

Next, it checks whether there is already a sqlite database present. If not, it creates one. It ensures there are entries for each youtube channel being scanned.

Then, it checks each transcript and if not already present in the sqlite database, it transforms it into JSON and ingests it into a table.

yt-dlp --write-auto-sub --skip-download --convert-subs=srt -o "%(id)s.%(ext)s" {VIDEO URL}

## Config File

Require config.json file to run. Example below.

```json
{
"database": "videos.db",
    "channels": [
        "https://www.youtube.com/{Person}"
    ]
}
```
