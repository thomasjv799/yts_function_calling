# YTS Movie Downloader — Discord Bot

An AI-powered Discord bot that finds and downloads movies on demand. Tell it what you want in plain English, it handles the rest.

## Vision

**Phase 1 (current):** Discord-first movie downloader
- Message the bot: "download Interstellar" or "get me that Tom Hanks movie about the island"
- LangGraph agent (powered by Groq) searches YTS, handles ambiguity, picks the best torrent automatically
- Downloads to a Plex-ready folder structure and notifies you on Discord when done

**Phase 2 (planned):** Plex integration
- Automatically sync downloaded movies with a self-hosted Plex Media Server
- Browse and watch directly through Plex

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

## Features

- **Natural language requests** — ask for movies by title, description, actor, or vibe
- **Ambiguity handling** — if multiple matches, bot asks you to clarify before downloading
- **Smart quality selection** — automatically picks the best torrent based on seeds and quality
- **Download queue** — track active, pending, and completed downloads
- **Duplicate detection** — won't re-download something you already have
- **Auto subtitles** — downloads subtitles alongside the movie
- **Plex-ready structure** — organizes files as `Movies/Title (Year)/Title (Year).mkv`
- **Discord notifications** — get notified with movie poster when download completes

## Tech Stack

- **Discord bot:** `discord.py`
- **AI agent:** LangGraph + Groq (function calling)
- **Database:** PostgreSQL (agent memory + download queue)
- **Torrents:** `libtorrent`
- **Movie source:** YTS API

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL
- A Discord bot token
- A Groq API key

### Installation

1. Clone the repository:
```bash
git clone [your-repository-url]
cd yts_function_calling
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file:
```
GROQ_API_KEY=your_groq_api_key
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_USER_ID=your_discord_user_id
DATABASE_URL=postgresql://user:password@localhost:5432/yts_bot
DOWNLOAD_PATH=/path/to/your/Movies
```

5. Initialize the database:
```bash
python -m scripts.init_db
```

6. Run the bot:
```bash
python main.py
```

## Usage

Message the bot in Discord:

```
download Interstellar
get me Inception
find the new Dune movie
what's downloading?
cancel Dune
```

## Project Structure

```
yts_function_calling/
├── main.py                 # Entry point — starts bot + worker
├── bot/
│   ├── client.py           # Discord bot client
│   └── handlers.py         # Message handlers
├── agent/
│   ├── graph.py            # LangGraph agent definition
│   └── tools.py            # Groq function calling tools
├── downloader/
│   ├── worker.py           # Background download worker
│   └── torrent.py          # libtorrent wrapper
├── db/
│   ├── models.py           # PostgreSQL models
│   └── queue.py            # Download queue operations
├── config.py               # Environment config
└── requirements.txt
```
