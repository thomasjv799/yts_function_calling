# Discord Movie Bot — Design Spec

**Date:** 2026-04-08  
**Status:** Approved

---

## Overview

An AI-powered Discord bot that lets you request movies in plain English, finds the best torrent on YTS, downloads it automatically, and notifies you when done. Downloads land in a Plex-ready folder structure for seamless Phase 2 Plex integration.

---

## Architecture

```
Discord User
     ↓
Discord Bot (discord.py)
     ↓
LangGraph Agent (Groq LLM + tools)
     ↓                    ↓
YTS API             PostgreSQL
(search)         (agent memory +
                  download queue)
                       ↓
               Download Worker
               (libtorrent, async)
                       ↓
            ~/Media/Movies/Title (Year)/
                       ↓
               Discord Notification
```

**Runtime:** Single Python process (`main.py`) starts the Discord bot and background download worker as concurrent asyncio tasks. No separate services required.

---

## Project Structure

```
yts_function_calling/
├── main.py                 # Entry point — starts bot + worker
├── bot/
│   ├── client.py           # Discord bot client, message routing
│   └── handlers.py         # Message handlers, Discord reply helpers
├── agent/
│   ├── graph.py            # LangGraph ReAct agent definition
│   └── tools.py            # Groq function calling tools
├── downloader/
│   ├── worker.py           # Async background download worker
│   └── torrent.py          # libtorrent wrapper
├── db/
│   ├── models.py           # SQLAlchemy models
│   └── queue.py            # Download queue CRUD operations
├── scripts/
│   └── init_db.py          # DB initialization script
├── config.py               # Environment config
└── requirements.txt
```

---

## LangGraph Agent

**Type:** ReAct-style graph  
**LLM:** Groq (fast inference, function calling support)  
**Memory:** PostgreSQL checkpointer keyed by Discord user ID — preserves conversation context across messages

### Tools

| Tool | Description |
|------|-------------|
| `search_movies` | Query YTS API by title with optional quality/rating filters |
| `get_movie_details` | Fetch poster URL, synopsis, rating, cast for a specific movie ID |
| `check_duplicate` | Check if movie already exists on disk or in the download queue |
| `queue_download` | Insert a download job into the Postgres queue |
| `get_queue_status` | Return active, pending, and completed downloads |
| `cancel_download` | Remove a pending job or stop an active one |

### Ambiguity Handling

If `search_movies` returns multiple close matches, the agent presents a numbered list in Discord and waits for the user to reply with a selection before calling `queue_download`. The LangGraph checkpointer preserves this mid-conversation state.

### Smart Quality Selection

When `queue_download` is called, the agent automatically selects the best available torrent using this priority:
1. Highest quality with seeds ≥ 20
2. If no torrent meets seed threshold, fall back to highest-seeded option
3. Prefer BluRay encode type over WEB

---

## Download Worker

Runs as an asyncio background task. Polls PostgreSQL every 5 seconds for `pending` jobs.

### Job Lifecycle

```
pending → downloading → done
                     ↘ failed
```

1. Worker claims a `pending` job by setting status to `downloading`
2. `libtorrent` session handles the download; worker updates `progress` and `speed` in Postgres every 10 seconds
3. On completion:
   - Moves file to Plex-ready path
   - Triggers subtitle download (OpenSubtitles API)
   - Sets status to `done`
   - Sends Discord notification with movie poster
4. On failure: sets status to `failed`, notifies user with error message

### Concurrency

Worker processes one download at a time. Multiple `libtorrent` sessions can be added later if needed.

---

## Database Schema

### `download_queue` table

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `movie_title` | TEXT | Movie title |
| `movie_year` | INT | Release year |
| `movie_id` | INT | YTS movie ID |
| `torrent_url` | TEXT | Torrent file URL |
| `quality` | TEXT | e.g. `1080p` |
| `status` | TEXT | `pending`, `downloading`, `done`, `failed`, `cancelled` |
| `progress` | FLOAT | 0.0–100.0 |
| `speed` | TEXT | Human-readable speed e.g. `2.4 MB/s` |
| `file_path` | TEXT | Final file path on disk |
| `discord_user_id` | TEXT | Discord user ID for notification |
| `error` | TEXT | Error message if failed |
| `created_at` | TIMESTAMP | When job was queued |
| `completed_at` | TIMESTAMP | When download finished |

### LangGraph checkpointer tables

Standard LangGraph PostgreSQL checkpointer tables (managed by the library).

---

## File Organization

Downloads are organized for Plex compatibility:

```
$DOWNLOAD_PATH/
  Inception (2010)/
    Inception (2010).mkv
    Inception (2010).en.srt
  Cast Away (2000)/
    Cast Away (2000).mkv
    Cast Away (2000).en.srt
```

---

## Discord Interaction

The bot listens to DMs. Every message is forwarded to the LangGraph agent. No command prefixes required — plain English only.

### Example Flows

**Standard download:**
```
User: download Inception
Bot:  🎬 Inception (2010) ★8.8
      Christopher Nolan's mind-bending heist thriller.
      Best available: 1080p BluRay (2.1 GB, 142 seeds)
      Download this? (yes/no)
User: yes
Bot:  ⏬ Queued! I'll ping you when it's done.
...
Bot:  ✅ Inception (2010) downloaded!
      [movie poster]
      Saved to Movies/Inception (2010)/Inception (2010).mkv
```

**Ambiguous request:**
```
User: download the Tom Hanks island movie
Bot:  Found 2 matches:
      1. Cast Away (2000) ★7.8
      2. The Terminal (2004) ★7.4
      Which one?
User: 1
Bot:  ⏬ Queued Cast Away (2000)!
```

**Status and management:**
```
User: what's downloading?
User: cancel Dune
User: do I have Interstellar?
```

---

## Environment Variables

```
GROQ_API_KEY=
DISCORD_BOT_TOKEN=
DISCORD_USER_ID=
DATABASE_URL=postgresql://user:password@localhost:5432/yts_bot
DOWNLOAD_PATH=/path/to/Movies
OPENSUBTITLES_API_KEY=       # optional, for auto subtitles
```

---

## Phase 2: Plex Integration (Out of Scope Now)

- Auto-trigger Plex library scan after download completes
- Discord notifications include a "Watch now" deep link to Plex
- Watchlist sync between Discord bot and Plex

---

## Out of Scope

- Web UI
- Multi-user support (single Discord user ID for now)
- TV show support (movies only)
- Streaming (download only)
