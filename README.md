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
    ],
    "ytdl_options": {
        "skip_download": true,
        "extract_flat": false,
        "flat_playlist": false,
        "ignoreerrors": true,
        "quiet": true,
        "no_warnings": true,
        "outtmpl": "dummy"
    },
    "apprise_endpoints": [
        "endpoint1",
        "endpoint2"
    ]
}
```

## Transcript Schema

YouTube's default format for captions is a "JSON3" format. Seems to be fairly straightforward. There are other formats available and also yt-dlp can convert into SRT, the most standard format, but JSON works well-enough so will be storing transcripts in database as JSON3 text. Easier to work with JSON programmatically anyway.

Most text appears to be in events. First event seems to be info about total runtime potentialy. From there, every other event (odd-numbered ones) appear to contain the actual subtitle text. Even-numbered events seem to just be a newline potentially, that's appending to each actual section of text?

Short example segment below.

```json
{
    "wireMagic": "pb3",
    "pens": [],
    "wsWinStyles": [],
    "wpWinPositions": [],
    "events": [
        {
            "dDurationMs": 3079920,
            "id": 1,
            "tStartMs": 0,
            "wpWinPosId": 1,
            "wsWinStyleId": 1
        },
        {
            "dDurationMs": 5121,
            "segs": [
                {
                    "acAsrConf": 0,
                    "utf8": "hello"
                },
                {
                    "acAsrConf": 0,
                    "tOffsetMs": 441,
                    "utf8": " and"
                },
                {
                    "acAsrConf": 0,
                    "tOffsetMs": 601,
                    "utf8": " welcome"
                },
                {
                    "acAsrConf": 0,
                    "tOffsetMs": 961,
                    "utf8": " back"
                },
                {
                    "acAsrConf": 0,
                    "tOffsetMs": 1081,
                    "utf8": " to"
                },
                {
                    "acAsrConf": 0,
                    "tOffsetMs": 1240,
                    "utf8": " Scarlet"
                },
                {
                    "acAsrConf": 0,
                    "tOffsetMs": 1681,
                    "utf8": " Hollow"
                }
            ],
            "tStartMs": 919,
            "wWinId": 1
        },
        {
            "aAppend": 1,
            "dDurationMs": 3010,
            "segs": [
                {
                    "utf8": "\n"
                }
            ],
            "tStartMs": 3030,
            "wWinId": 1
        },
        {
            "dDurationMs": 6639,
            "segs": [
                {
                    "acAsrConf": 0,
                    "utf8": "we"
                },
                {
                    "acAsrConf": 0,
                    "tOffsetMs": 80,
                    "utf8": " are"
                },
                {
                    "acAsrConf": 0,
                    "tOffsetMs": 280,
                    "utf8": " about"
                },
                {
                    "acAsrConf": 0,
                    "tOffsetMs": 520,
                    "utf8": " to"
                },
                {
                    "acAsrConf": 0,
                    "tOffsetMs": 720,
                    "utf8": " begin"
                },
                {
                    "acAsrConf": 0,
                    "tOffsetMs": 1239,
                    "utf8": " episode"
                },
                {
                    "acAsrConf": 0,
                    "tOffsetMs": 1839,
                    "utf8": " two"
                },
                {
                    "acAsrConf": 0,
                    "tOffsetMs": 2839,
                    "utf8": " would"
                }
            ],
            "tStartMs": 3040,
            "wWinId": 1
        },
        {
            "aAppend": 1,
            "dDurationMs": 3649,
            "segs": [
                {
                    "utf8": "\n"
                }
            ],
            "tStartMs": 6030,
            "wWinId": 1
        },
        {
            "dDurationMs": 7040,
            "segs": [
                {
                    "acAsrConf": 0,
                    "utf8": "you"
                },
                {
                    "acAsrConf": 0,
                    "tOffsetMs": 120,
                    "utf8": " like"
                },
                {
                    "acAsrConf": 0,
                    "tOffsetMs": 279,
                    "utf8": " to"
                },
                {
                    "acAsrConf": 0,
                    "tOffsetMs": 359,
                    "utf8": " see"
                },
                {
                    "acAsrConf": 0,
                    "tOffsetMs": 560,
                    "utf8": " a"
                },
                {
                    "acAsrConf": 0,
                    "tOffsetMs": 1200,
                    "utf8": " no"
                },
                {
                    "acAsrConf": 0,
                    "tOffsetMs": 2080,
                    "utf8": " I"
                },
                {
                    "acAsrConf": 0,
                    "tOffsetMs": 2240,
                    "utf8": " just"
                },
                {
                    "acAsrConf": 0,
                    "tOffsetMs": 2440,
                    "utf8": " did"
                },
                {
                    "acAsrConf": 0,
                    "tOffsetMs": 2720,
                    "utf8": " it"
                }
            ],
            "tStartMs": 6040,
            "wWinId": 1
        }
    ]
}
```
