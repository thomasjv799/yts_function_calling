# Discord Movie Bot — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the existing FastAPI movie search app with a Discord bot that lets users request movies in plain English, downloads them via libtorrent, and notifies via Discord on completion.

**Architecture:** A single Python process starts a Discord bot (discord.py v2) and an async background download worker via `setup_hook`. A LangGraph ReAct agent (Groq LLM) handles user messages, searches YTS via function calling, and queues download jobs. PostgreSQL stores both LangGraph conversation checkpoints and the download queue.

**Tech Stack:** `discord.py>=2.3`, `langgraph>=0.2`, `langgraph-checkpoint-postgres`, `langchain-groq`, `langchain-core`, `sqlalchemy[asyncio]>=2.0`, `asyncpg`, `psycopg[binary]>=3.1`, `psycopg-pool>=3.1`, `libtorrent`, `subliminal`, `babelfish`, `httpx`, `pytest`, `pytest-asyncio`, `respx`

---

## File Map

```
main.py                       Entry point — starts bot (worker runs inside via setup_hook)
config.py                     Environment config (rewrite)
requirements.txt              Dependencies (rewrite)
bot/
  __init__.py
  client.py                   MovieBot(discord.Client) — registers on_message, setup_hook
  handlers.py                 handle_message, send_completion_notification, send_failure_notification
agent/
  __init__.py
  quality.py                  select_best_torrent() — pure quality selection logic
  tools.py                    search_movies, get_movie_details, get_poster_url, build_queue_tools()
  graph.py                    get_agent() — LangGraph ReAct agent with Postgres checkpointer
downloader/
  __init__.py
  torrent.py                  download_torrent() — async libtorrent wrapper
  subtitles.py                download_subtitles() — subliminal wrapper, best-effort
  worker.py                   run_worker(), process_job() — polls queue, downloads, notifies
db/
  __init__.py
  models.py                   DownloadJob SQLAlchemy model
  queue.py                    init_db, add_job, get_pending_job, update_job, get_all_jobs,
                              cancel_job_by_title, check_duplicate
scripts/
  __init__.py
  init_db.py                  One-time DB init script
tests/
  __init__.py
  test_quality.py
  test_queue.py
  test_tools.py
  test_torrent.py
  test_worker.py
  test_handlers.py
```

---

## Task 1: Clean up legacy code and scaffold new structure

**Files:**
- Delete: `movie_search.py`, `server.py`, `templates/index.html`
- Rewrite: `config.py`, `requirements.txt`
- Create: `bot/__init__.py`, `agent/__init__.py`, `downloader/__init__.py`, `db/__init__.py`, `scripts/__init__.py`, `tests/__init__.py`, `pytest.ini`

- [ ] **Step 1: Remove legacy files**

```bash
git rm movie_search.py server.py templates/index.html
rmdir templates
```

Expected output: `rm 'movie_search.py'`, `rm 'server.py'`, `rm 'templates/index.html'`

- [ ] **Step 2: Rewrite config.py**

```python
# config.py
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")
    DISCORD_USER_ID: str = os.getenv("DISCORD_USER_ID", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    DOWNLOAD_PATH: str = os.getenv("DOWNLOAD_PATH", "./downloads")
    OPENSUBTITLES_USERNAME: str = os.getenv("OPENSUBTITLES_USERNAME", "")
    OPENSUBTITLES_PASSWORD: str = os.getenv("OPENSUBTITLES_PASSWORD", "")
    WORKER_POLL_INTERVAL: int = int(os.getenv("WORKER_POLL_INTERVAL", "5"))

    @staticmethod
    def validate() -> None:
        required = ["GROQ_API_KEY", "DISCORD_BOT_TOKEN", "DISCORD_USER_ID", "DATABASE_URL"]
        missing = [k for k in required if not getattr(Config, k)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    @staticmethod
    def async_db_url() -> str:
        return Config.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
```

- [ ] **Step 3: Rewrite requirements.txt**

```
discord.py>=2.3.0
langgraph>=0.2.0
langgraph-checkpoint-postgres
langchain-groq
langchain-core
sqlalchemy[asyncio]>=2.0.0
asyncpg
psycopg[binary]>=3.1.0
psycopg-pool>=3.1.0
libtorrent
subliminal
babelfish
httpx>=0.24.1
python-dotenv>=0.19.0
pytest>=7.4.0
pytest-asyncio>=0.23.0
respx>=0.20.0
```

- [ ] **Step 4: Create package directories and pytest config**

```bash
mkdir -p bot agent downloader db scripts tests
touch bot/__init__.py agent/__init__.py downloader/__init__.py db/__init__.py scripts/__init__.py tests/__init__.py
```

Create `pytest.ini`:
```ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 5: Install dependencies**

```bash
pip install -r requirements.txt
```

Note: `libtorrent` requires the system library. On macOS: `brew install libtorrent-rasterbar` before pip install.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: remove legacy app, scaffold Discord bot project structure"
```

---

## Task 2: Database models and download queue

**Files:**
- Create: `db/models.py`
- Create: `db/queue.py`
- Create: `tests/test_queue.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_queue.py
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_add_job_calls_session_add_and_commit():
    mock_job = MagicMock()
    mock_job.id = uuid.uuid4()

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("db.queue.AsyncSessionLocal", return_value=mock_session):
        from db.queue import add_job
        await add_job("Inception", 2010, 1, "http://t.co/t.torrent", "1080p", "123456")
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_check_duplicate_returns_true_when_job_exists():
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = MagicMock()

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("db.queue.AsyncSessionLocal", return_value=mock_session):
        from db.queue import check_duplicate
        result = await check_duplicate("Inception", 2010)
        assert result is True


@pytest.mark.asyncio
async def test_check_duplicate_returns_false_when_no_job():
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("db.queue.AsyncSessionLocal", return_value=mock_session):
        from db.queue import check_duplicate
        result = await check_duplicate("Unknown Movie", 2099)
        assert result is False
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_queue.py -v
```

Expected: `ModuleNotFoundError: No module named 'db.queue'`

- [ ] **Step 3: Write db/models.py**

```python
# db/models.py
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class DownloadJob(Base):
    __tablename__ = "download_queue"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    movie_title: Mapped[str] = mapped_column(String, nullable=False)
    movie_year: Mapped[int] = mapped_column(Integer, nullable=False)
    movie_id: Mapped[int] = mapped_column(Integer, nullable=False)
    torrent_url: Mapped[str] = mapped_column(Text, nullable=False)
    quality: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    speed: Mapped[str] = mapped_column(String, default="")
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    discord_user_id: Mapped[str] = mapped_column(String, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

- [ ] **Step 4: Write db/queue.py**

```python
# db/queue.py
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from db.models import Base, DownloadJob
from config import Config

engine = create_async_engine(Config.async_db_url())
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def add_job(
    movie_title: str,
    movie_year: int,
    movie_id: int,
    torrent_url: str,
    quality: str,
    discord_user_id: str,
) -> DownloadJob:
    async with AsyncSessionLocal() as session:
        job = DownloadJob(
            movie_title=movie_title,
            movie_year=movie_year,
            movie_id=movie_id,
            torrent_url=torrent_url,
            quality=quality,
            discord_user_id=discord_user_id,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job


async def get_pending_job() -> DownloadJob | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(DownloadJob)
            .where(DownloadJob.status == "pending")
            .order_by(DownloadJob.created_at)
            .limit(1)
        )
        return result.scalar_one_or_none()


async def update_job(job_id: uuid.UUID, **kwargs) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(DownloadJob).where(DownloadJob.id == job_id))
        job = result.scalar_one()
        for key, value in kwargs.items():
            setattr(job, key, value)
        await session.commit()


async def get_all_jobs(limit: int = 20) -> list[DownloadJob]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(DownloadJob).order_by(DownloadJob.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())


async def cancel_job_by_title(movie_title: str) -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(DownloadJob)
            .where(DownloadJob.movie_title.ilike(f"%{movie_title}%"))
            .where(DownloadJob.status == "pending")
            .limit(1)
        )
        job = result.scalar_one_or_none()
        if not job:
            return False
        job.status = "cancelled"
        await session.commit()
        return True


async def check_duplicate(movie_title: str, movie_year: int) -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(DownloadJob)
            .where(DownloadJob.movie_title.ilike(f"%{movie_title}%"))
            .where(DownloadJob.movie_year == movie_year)
            .where(DownloadJob.status.in_(["pending", "downloading", "done"]))
            .limit(1)
        )
        return result.scalar_one_or_none() is not None
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_queue.py -v
```

Expected: `3 passed`

- [ ] **Step 6: Commit**

```bash
git add db/ tests/test_queue.py
git commit -m "feat: add database models and download queue operations"
```

---

## Task 3: Smart quality selection

**Files:**
- Create: `agent/quality.py`
- Create: `tests/test_quality.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_quality.py
from agent.quality import select_best_torrent


def test_prefers_1080p_bluray_with_good_seeds():
    torrents = [
        {"quality": "720p", "type": "web", "seeds": 50, "url": "http://a.com/720p.torrent"},
        {"quality": "1080p", "type": "bluray", "seeds": 80, "url": "http://a.com/1080p.torrent"},
        {"quality": "2160p", "type": "web", "seeds": 3, "url": "http://a.com/4k.torrent"},
    ]
    result = select_best_torrent(torrents)
    assert result["quality"] == "1080p"
    assert result["type"] == "bluray"


def test_falls_back_to_highest_seeded_when_no_torrent_meets_threshold():
    torrents = [
        {"quality": "1080p", "type": "bluray", "seeds": 2, "url": "http://a.com/1080p.torrent"},
        {"quality": "720p", "type": "web", "seeds": 15, "url": "http://a.com/720p.torrent"},
    ]
    result = select_best_torrent(torrents)
    assert result["seeds"] == 15


def test_returns_none_for_empty_list():
    assert select_best_torrent([]) is None


def test_prefers_2160p_over_1080p_when_both_have_good_seeds():
    torrents = [
        {"quality": "1080p", "type": "bluray", "seeds": 100, "url": "http://a.com/1080p.torrent"},
        {"quality": "2160p", "type": "bluray", "seeds": 30, "url": "http://a.com/4k.torrent"},
    ]
    result = select_best_torrent(torrents)
    assert result["quality"] == "2160p"


def test_prefers_bluray_over_web_at_same_quality():
    torrents = [
        {"quality": "1080p", "type": "web", "seeds": 50, "url": "http://a.com/web.torrent"},
        {"quality": "1080p", "type": "bluray", "seeds": 30, "url": "http://a.com/bluray.torrent"},
    ]
    result = select_best_torrent(torrents)
    assert result["type"] == "bluray"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_quality.py -v
```

Expected: `ModuleNotFoundError: No module named 'agent.quality'`

- [ ] **Step 3: Write agent/quality.py**

```python
# agent/quality.py
QUALITY_RANK = {"2160p": 3, "1080p": 2, "720p": 1}
TYPE_RANK = {"bluray": 2, "web": 1}
SEED_THRESHOLD = 20


def select_best_torrent(torrents: list[dict]) -> dict | None:
    """Select the best torrent from a list.

    Among torrents with seeds >= 20, picks the highest quality + BluRay type.
    Falls back to the highest-seeded torrent if none meet the seed threshold.
    """
    if not torrents:
        return None

    candidates = [t for t in torrents if t.get("seeds", 0) >= SEED_THRESHOLD]
    if not candidates:
        candidates = torrents

    def score(t: dict) -> tuple[int, int, int]:
        quality = QUALITY_RANK.get(t.get("quality", ""), 0)
        kind = TYPE_RANK.get(t.get("type", "").lower(), 0)
        seeds = t.get("seeds", 0)
        return (quality, kind, seeds)

    return max(candidates, key=score)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_quality.py -v
```

Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add agent/quality.py tests/test_quality.py
git commit -m "feat: add smart torrent quality selection"
```

---

## Task 4: YTS search tools

**Files:**
- Create: `agent/tools.py`
- Create: `tests/test_tools.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_tools.py
import pytest
import respx
import httpx

YTS_LIST_URL = "https://yts.mx/api/v2/list_movies.json"
YTS_DETAIL_URL = "https://yts.mx/api/v2/movie_details.json"


@pytest.mark.asyncio
@respx.mock
async def test_search_movies_returns_formatted_results():
    respx.get(YTS_LIST_URL).mock(return_value=httpx.Response(200, json={
        "status": "ok",
        "data": {
            "movie_count": 1,
            "movies": [{
                "id": 1,
                "title": "Inception",
                "year": 2010,
                "rating": 8.8,
                "torrents": [{"quality": "1080p"}],
            }],
        },
    }))
    from agent.tools import search_movies
    result = await search_movies.ainvoke({"query": "Inception"})
    assert "Inception" in result
    assert "2010" in result
    assert "8.8" in result


@pytest.mark.asyncio
@respx.mock
async def test_search_movies_returns_no_results_message():
    respx.get(YTS_LIST_URL).mock(return_value=httpx.Response(200, json={
        "status": "ok",
        "data": {"movie_count": 0},
    }))
    from agent.tools import search_movies
    result = await search_movies.ainvoke({"query": "xyznotamovie"})
    assert "No movies found" in result


@pytest.mark.asyncio
@respx.mock
async def test_get_movie_details_returns_synopsis_and_torrents():
    respx.get(YTS_DETAIL_URL).mock(return_value=httpx.Response(200, json={
        "status": "ok",
        "data": {
            "movie": {
                "id": 1,
                "title": "Inception",
                "year": 2010,
                "rating": 8.8,
                "description_full": "A thief who steals corporate secrets.",
                "large_cover_image": "https://img.yts.mx/inception.jpg",
                "torrents": [
                    {"quality": "1080p", "type": "bluray", "size": "2.1 GB",
                     "seeds": 142, "url": "http://t.co/inception.torrent"},
                ],
            }
        },
    }))
    from agent.tools import get_movie_details
    result = await get_movie_details.ainvoke({"movie_id": 1})
    assert "Inception" in result
    assert "A thief" in result
    assert "1080p" in result
    assert "142" in result


@pytest.mark.asyncio
@respx.mock
async def test_get_poster_url_returns_image_url():
    respx.get(YTS_DETAIL_URL).mock(return_value=httpx.Response(200, json={
        "status": "ok",
        "data": {"movie": {"large_cover_image": "https://img.yts.mx/inception.jpg"}},
    }))
    from agent.tools import get_poster_url
    url = await get_poster_url(1)
    assert url == "https://img.yts.mx/inception.jpg"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_tools.py -v
```

Expected: `ModuleNotFoundError: No module named 'agent.tools'`

- [ ] **Step 3: Write agent/tools.py**

```python
# agent/tools.py
from typing import Optional
import httpx
from langchain_core.tools import tool

YTS_BASE = "https://yts.mx/api/v2"


@tool
async def search_movies(query: str, quality: Optional[str] = None, minimum_rating: float = 0) -> str:
    """Search for movies on YTS by title. Returns up to 5 matches with IDs, years, and ratings."""
    params: dict = {"query_term": query, "limit": 5, "with_rt_ratings": "true"}
    if quality:
        params["quality"] = quality
    if minimum_rating > 0:
        params["minimum_rating"] = minimum_rating

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{YTS_BASE}/list_movies.json", params=params)
        data = resp.json()

    if data["status"] != "ok" or not data["data"].get("movie_count"):
        return "No movies found."

    lines = []
    for m in data["data"]["movies"][:5]:
        qualities = [t["quality"] for t in m.get("torrents", [])]
        lines.append(
            f"ID:{m['id']} | {m['title']} ({m['year']}) | "
            f"Rating: {m['rating']} | Available: {', '.join(qualities)}"
        )
    return "\n".join(lines)


@tool
async def get_movie_details(movie_id: int) -> str:
    """Get full details for a movie: synopsis, rating, and available torrents with seeds and size."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{YTS_BASE}/movie_details.json",
            params={"movie_id": movie_id, "with_images": True, "with_cast": True},
        )
        data = resp.json()

    if data["status"] != "ok":
        return "Movie not found."

    m = data["data"]["movie"]
    torrent_lines = [
        f"  {t['quality']} {t['type']} | {t['size']} | Seeds: {t['seeds']} | {t['url']}"
        for t in m.get("torrents", [])
    ]
    synopsis = m.get("description_full", "N/A")[:300]
    return (
        f"{m['title']} ({m['year']}) — ★{m['rating']}\n"
        f"{synopsis}\n"
        f"Poster: {m.get('large_cover_image', '')}\n"
        f"Torrents:\n" + "\n".join(torrent_lines)
    )


async def get_poster_url(movie_id: int) -> str:
    """Fetch the large cover image URL for a movie. Used for Discord notifications."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{YTS_BASE}/movie_details.json",
            params={"movie_id": movie_id, "with_images": True},
        )
        data = resp.json()
    if data["status"] != "ok":
        return ""
    return data["data"]["movie"].get("large_cover_image", "")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_tools.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add agent/tools.py tests/test_tools.py
git commit -m "feat: add YTS search and movie detail tools"
```

---

## Task 5: Queue management tools

**Files:**
- Modify: `agent/tools.py` (append `build_queue_tools`)
- Modify: `tests/test_tools.py` (append queue tool tests)

- [ ] **Step 1: Write the failing tests** (append to `tests/test_tools.py`)

```python
# Append to tests/test_tools.py
import uuid
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_check_duplicate_tool_returns_already_queued():
    with patch("db.queue.check_duplicate", new=AsyncMock(return_value=True)):
        from agent.tools import build_queue_tools
        tools = build_queue_tools("123456")
        check_dup = next(t for t in tools if t.name == "check_duplicate")
        result = await check_dup.ainvoke({"movie_title": "Inception", "movie_year": 2010})
        assert "already" in result.lower()


@pytest.mark.asyncio
async def test_check_duplicate_tool_returns_not_in_queue():
    with patch("db.queue.check_duplicate", new=AsyncMock(return_value=False)):
        from agent.tools import build_queue_tools
        tools = build_queue_tools("123456")
        check_dup = next(t for t in tools if t.name == "check_duplicate")
        result = await check_dup.ainvoke({"movie_title": "Unknown", "movie_year": 2020})
        assert "not in" in result.lower()


@pytest.mark.asyncio
async def test_queue_download_tool_calls_add_job():
    mock_job = MagicMock()
    mock_job.id = uuid.uuid4()
    with patch("db.queue.add_job", new=AsyncMock(return_value=mock_job)):
        from agent.tools import build_queue_tools
        tools = build_queue_tools("123456")
        queue_dl = next(t for t in tools if t.name == "queue_download")
        result = await queue_dl.ainvoke({
            "movie_title": "Inception",
            "movie_year": 2010,
            "movie_id": 1,
            "torrent_url": "http://t.co/t.torrent",
            "quality": "1080p",
        })
        assert "Queued" in result
        assert "Inception" in result


@pytest.mark.asyncio
async def test_cancel_download_tool_returns_cancelled():
    with patch("db.queue.cancel_job_by_title", new=AsyncMock(return_value=True)):
        from agent.tools import build_queue_tools
        tools = build_queue_tools("123456")
        cancel = next(t for t in tools if t.name == "cancel_download")
        result = await cancel.ainvoke({"movie_title": "Inception"})
        assert "Cancelled" in result


@pytest.mark.asyncio
async def test_cancel_download_tool_returns_not_found():
    with patch("db.queue.cancel_job_by_title", new=AsyncMock(return_value=False)):
        from agent.tools import build_queue_tools
        tools = build_queue_tools("123456")
        cancel = next(t for t in tools if t.name == "cancel_download")
        result = await cancel.ainvoke({"movie_title": "Unknown"})
        assert "No pending" in result
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_tools.py -k "queue or cancel or duplicate" -v
```

Expected: `AttributeError` or `ImportError` — `build_queue_tools` does not exist yet

- [ ] **Step 3: Append `build_queue_tools` to agent/tools.py**

```python
# Append to agent/tools.py
from db import queue as db_queue


def build_queue_tools(discord_user_id: str) -> list:
    """Create queue management tools with discord_user_id baked into queue_download."""

    @tool
    async def check_duplicate(movie_title: str, movie_year: int) -> str:
        """Check if a movie is already downloaded or in the download queue."""
        exists = await db_queue.check_duplicate(movie_title, movie_year)
        if exists:
            return f"{movie_title} ({movie_year}) is already in the queue or downloaded."
        return f"{movie_title} ({movie_year}) is not in the queue."

    @tool
    async def queue_download(
        movie_title: str, movie_year: int, movie_id: int, torrent_url: str, quality: str
    ) -> str:
        """Queue a movie for download after the user has confirmed."""
        job = await db_queue.add_job(
            movie_title, movie_year, movie_id, torrent_url, quality, discord_user_id
        )
        return f"Queued {movie_title} ({movie_year}) [{quality}]. Job ID: {job.id}"

    @tool
    async def get_queue_status() -> str:
        """Get the current status of all downloads (downloading, pending, done, failed)."""
        jobs = await db_queue.get_all_jobs()
        if not jobs:
            return "No downloads in queue."
        status_map = {
            "downloading": lambda j: f"⏬ {j.movie_title} ({j.movie_year}) — {j.progress:.0f}% at {j.speed}",
            "pending": lambda j: f"⏳ {j.movie_title} ({j.movie_year}) — pending",
            "done": lambda j: f"✅ {j.movie_title} ({j.movie_year}) — done",
            "failed": lambda j: f"❌ {j.movie_title} ({j.movie_year}) — failed: {j.error}",
            "cancelled": lambda j: f"🚫 {j.movie_title} ({j.movie_year}) — cancelled",
        }
        lines = [status_map.get(j.status, lambda j: f"? {j.movie_title}")(j) for j in jobs]
        return "\n".join(lines)

    @tool
    async def cancel_download(movie_title: str) -> str:
        """Cancel a pending download by movie title."""
        success = await db_queue.cancel_job_by_title(movie_title)
        if success:
            return f"Cancelled download for {movie_title}."
        return f"No pending download found for {movie_title}."

    return [check_duplicate, queue_download, get_queue_status, cancel_download]
```

- [ ] **Step 4: Run all tool tests**

```bash
pytest tests/test_tools.py -v
```

Expected: `9 passed`

- [ ] **Step 5: Commit**

```bash
git add agent/tools.py tests/test_tools.py
git commit -m "feat: add queue management tools with injected discord_user_id"
```

---

## Task 6: LangGraph agent

**Files:**
- Create: `agent/graph.py`
- Create: `tests/test_agent.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_agent.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_get_agent_returns_runnable():
    mock_pool = MagicMock()
    mock_pool.open = AsyncMock()

    mock_checkpointer = MagicMock()
    mock_checkpointer.setup = AsyncMock()

    with patch("agent.graph.AsyncConnectionPool", return_value=mock_pool), \
         patch("agent.graph.AsyncPostgresSaver", return_value=mock_checkpointer):
        from agent.graph import get_agent
        agent = await get_agent("123456")
        assert agent is not None
        assert hasattr(agent, "ainvoke")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_agent.py -v
```

Expected: `ModuleNotFoundError: No module named 'agent.graph'`

- [ ] **Step 3: Write agent/graph.py**

```python
# agent/graph.py
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_groq import ChatGroq
from psycopg_pool import AsyncConnectionPool
from agent.tools import search_movies, get_movie_details, build_queue_tools
from config import Config

_checkpointer: AsyncPostgresSaver | None = None
_pool: AsyncConnectionPool | None = None

SYSTEM_PROMPT = """You are a movie download assistant for a personal media server.

When a user asks to download a movie:
1. Call check_duplicate to see if it's already queued or downloaded.
2. Call search_movies to find it.
3. If there are 2+ close matches, list them numbered and ask the user to pick one.
4. Call get_movie_details on the chosen movie — show title, year, rating, and a short synopsis.
5. Ask "Download this? (yes/no)" and wait for confirmation.
6. On confirmation, pick the best torrent from the details (prefer 1080p+ BluRay with seeds >= 20)
   and call queue_download with the torrent URL and quality.
7. Confirm the movie is queued.

For status requests use get_queue_status. For cancellation use cancel_download.
Be concise. Plain text only — no markdown headers or bold."""


async def _get_checkpointer() -> AsyncPostgresSaver:
    global _checkpointer, _pool
    if _checkpointer is None:
        _pool = AsyncConnectionPool(
            conninfo=Config.DATABASE_URL,
            max_size=10,
            kwargs={"autocommit": True, "prepare_threshold": 0},
        )
        await _pool.open()
        _checkpointer = AsyncPostgresSaver(_pool)
        await _checkpointer.setup()
    return _checkpointer


async def get_agent(discord_user_id: str):
    """Create a ReAct agent for the given Discord user backed by the shared Postgres checkpointer."""
    checkpointer = await _get_checkpointer()
    llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=Config.GROQ_API_KEY)
    tools = [search_movies, get_movie_details] + build_queue_tools(discord_user_id)

    return create_react_agent(
        llm,
        tools,
        checkpointer=checkpointer,
        state_modifier=SYSTEM_PROMPT,
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_agent.py -v
```

Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add agent/graph.py tests/test_agent.py
git commit -m "feat: add LangGraph ReAct agent with Groq and Postgres checkpointer"
```

---

## Task 7: libtorrent wrapper

**Files:**
- Create: `downloader/torrent.py`
- Create: `tests/test_torrent.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_torrent.py
import pytest
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_download_torrent_returns_largest_file_path(tmp_path):
    mock_files = MagicMock()
    mock_files.num_files.return_value = 2
    mock_files.file_path.side_effect = ["subs/sub.srt", "Inception (2010).mkv"]
    mock_files.file_size.side_effect = [10_000, 2_000_000_000]

    mock_info = MagicMock()
    mock_info.files.return_value = mock_files

    mock_handle = MagicMock()
    mock_handle.is_seed.side_effect = [False, True]
    mock_handle.get_torrent_info.return_value = mock_info
    mock_status = MagicMock()
    mock_status.progress = 1.0
    mock_status.download_rate = 1024 * 1024
    mock_handle.status.return_value = mock_status

    mock_session = MagicMock()
    mock_session.add_torrent.return_value = mock_handle

    progress_calls = []

    async def on_progress(pct, speed):
        progress_calls.append((pct, speed))

    mock_lt = MagicMock()
    mock_lt.session.return_value = mock_session
    mock_lt.add_torrent_params.return_value = MagicMock()

    with patch("downloader.torrent.lt", mock_lt):
        from downloader.torrent import download_torrent
        result = await download_torrent(
            "http://example.com/inception.torrent",
            str(tmp_path),
            on_progress,
        )

    assert result.endswith("Inception (2010).mkv")
    assert len(progress_calls) >= 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_torrent.py -v
```

Expected: `ModuleNotFoundError: No module named 'downloader.torrent'`

- [ ] **Step 3: Write downloader/torrent.py**

```python
# downloader/torrent.py
import asyncio
import os
import time
from typing import Callable, Awaitable

try:
    import libtorrent as lt
except ImportError:
    lt = None  # Allows module to load in test environments without libtorrent installed


async def download_torrent(
    torrent_url: str,
    save_path: str,
    progress_callback: Callable[[float, str], Awaitable[None]] | None = None,
) -> str:
    """Download a torrent from URL to save_path.

    Returns the absolute path of the largest file in the torrent (the video file).
    Calls progress_callback(percent, speed_str) approximately every 2 seconds.
    """
    loop = asyncio.get_event_loop()
    callback_queue: asyncio.Queue = asyncio.Queue()

    def sync_download() -> str:
        if lt is None:
            raise RuntimeError("libtorrent is not installed. Run: brew install libtorrent-rasterbar && pip install libtorrent")

        ses = lt.session({"listen_interfaces": "0.0.0.0:6881"})
        params = lt.add_torrent_params()
        params.url = torrent_url
        params.save_path = save_path
        h = ses.add_torrent(params)

        while not h.is_seed():
            s = h.status()
            pct = s.progress * 100
            speed = f"{s.download_rate / 1024:.1f} KB/s"
            loop.call_soon_threadsafe(callback_queue.put_nowait, (pct, speed))
            time.sleep(2)

        loop.call_soon_threadsafe(callback_queue.put_nowait, None)  # sentinel

        info = h.get_torrent_info()
        files = info.files()
        largest_idx = max(range(files.num_files()), key=lambda i: files.file_size(i))
        return os.path.join(save_path, files.file_path(largest_idx))

    future = loop.run_in_executor(None, sync_download)

    while True:
        try:
            item = callback_queue.get_nowait()
        except asyncio.QueueEmpty:
            if future.done():
                break
            await asyncio.sleep(0.5)
            continue

        if item is None:
            break
        if progress_callback:
            pct, speed = item
            await progress_callback(pct, speed)

    return await future
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_torrent.py -v
```

Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add downloader/torrent.py tests/test_torrent.py
git commit -m "feat: add async libtorrent wrapper"
```

---

## Task 8: Download worker

**Files:**
- Create: `downloader/worker.py`
- Create: `tests/test_worker.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_worker.py
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch


def make_mock_job():
    job = MagicMock()
    job.id = uuid.uuid4()
    job.movie_title = "Inception"
    job.movie_year = 2010
    job.movie_id = 1
    job.torrent_url = "http://example.com/inception.torrent"
    job.quality = "1080p"
    job.discord_user_id = "123456"
    return job


@pytest.mark.asyncio
async def test_process_job_marks_done_and_calls_notify(tmp_path):
    job = make_mock_job()
    fake_file = tmp_path / "Inception.mkv"
    fake_file.write_text("fake")

    notify_calls = []

    async def mock_notify(j, path, error=None):
        notify_calls.append((j, path, error))

    with patch("downloader.worker.update_job", new=AsyncMock()), \
         patch("downloader.worker.download_torrent", new=AsyncMock(return_value=str(fake_file))), \
         patch("downloader.worker.download_subtitles", new=AsyncMock()), \
         patch("downloader.worker.Config") as mock_cfg, \
         patch("os.makedirs"), \
         patch("os.rename"):
        mock_cfg.DOWNLOAD_PATH = str(tmp_path)
        mock_cfg.WORKER_POLL_INTERVAL = 0

        from downloader.worker import process_job
        await process_job(job, mock_notify)

    assert len(notify_calls) == 1
    called_job, called_path, called_error = notify_calls[0]
    assert called_error is None
    assert called_job is job


@pytest.mark.asyncio
async def test_process_job_marks_failed_and_notifies_on_error():
    job = make_mock_job()
    notify_calls = []

    async def mock_notify(j, path, error=None):
        notify_calls.append((j, path, error))

    with patch("downloader.worker.update_job", new=AsyncMock()), \
         patch("downloader.worker.download_torrent", new=AsyncMock(side_effect=RuntimeError("no peers"))), \
         patch("downloader.worker.download_subtitles", new=AsyncMock()), \
         patch("downloader.worker.Config") as mock_cfg, \
         patch("os.makedirs"):
        mock_cfg.DOWNLOAD_PATH = "/tmp/movies"
        mock_cfg.WORKER_POLL_INTERVAL = 0

        from downloader.worker import process_job
        await process_job(job, mock_notify)

    assert len(notify_calls) == 1
    assert notify_calls[0][2] == "no peers"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_worker.py -v
```

Expected: `ModuleNotFoundError: No module named 'downloader.worker'`

- [ ] **Step 3: Write downloader/worker.py**

```python
# downloader/worker.py
import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Callable

from db.queue import get_pending_job, update_job
from db.models import DownloadJob
from downloader.torrent import download_torrent
from downloader.subtitles import download_subtitles
from config import Config


async def run_worker(notify_callback: Callable) -> None:
    """Poll the download queue indefinitely and process jobs as they arrive."""
    while True:
        job = await get_pending_job()
        if job:
            await process_job(job, notify_callback)
        await asyncio.sleep(Config.WORKER_POLL_INTERVAL)


async def process_job(job: DownloadJob, notify_callback: Callable) -> None:
    """Download one job, rename to Plex structure, download subtitles, and notify."""
    await update_job(job.id, status="downloading")

    tmp_dir = os.path.join(Config.DOWNLOAD_PATH, "tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    async def on_progress(pct: float, speed: str) -> None:
        await update_job(job.id, progress=pct, speed=speed)

    try:
        raw_path = await download_torrent(job.torrent_url, tmp_dir, on_progress)

        final_dir = Path(Config.DOWNLOAD_PATH) / f"{job.movie_title} ({job.movie_year})"
        final_dir.mkdir(parents=True, exist_ok=True)

        ext = Path(raw_path).suffix
        final_path = str(final_dir / f"{job.movie_title} ({job.movie_year}){ext}")
        os.rename(raw_path, final_path)

        await download_subtitles(final_path, job.movie_title, job.movie_year)

        await update_job(
            job.id,
            status="done",
            file_path=final_path,
            progress=100.0,
            speed="",
            completed_at=datetime.utcnow(),
        )
        await notify_callback(job, final_path)

    except Exception as exc:
        await update_job(job.id, status="failed", error=str(exc))
        await notify_callback(job, None, error=str(exc))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_worker.py -v
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add downloader/worker.py tests/test_worker.py
git commit -m "feat: add async download worker with Plex-ready file organization"
```

---

## Task 9: Subtitle downloader

**Files:**
- Create: `downloader/subtitles.py`

No unit test — `subliminal` makes external network calls. The worker tests already mock `download_subtitles`. Verify manually end-to-end.

- [ ] **Step 1: Write downloader/subtitles.py**

```python
# downloader/subtitles.py
import asyncio
import logging

logger = logging.getLogger(__name__)


async def download_subtitles(file_path: str, movie_title: str, movie_year: int) -> bool:
    """Download English subtitles for file_path using subliminal.

    Returns True if subtitles were saved. Failures are logged but never raised —
    subtitle download is best-effort and should not block the download completion flow.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _download_sync, file_path)


def _download_sync(file_path: str) -> bool:
    try:
        import subliminal
        from babelfish import Language

        video = subliminal.scan_video(file_path)
        subtitles = subliminal.download_best_subtitles([video], {Language("eng")})
        if subtitles.get(video):
            subliminal.save_subtitles(video, subtitles[video])
            logger.info("Subtitles saved for %s", file_path)
            return True
        logger.info("No subtitles found for %s", file_path)
        return False
    except Exception as exc:
        logger.warning("Subtitle download failed for %s: %s", file_path, exc)
        return False
```

- [ ] **Step 2: Commit**

```bash
git add downloader/subtitles.py
git commit -m "feat: add subtitle downloader (best-effort English subtitles via subliminal)"
```

---

## Task 10: Discord bot client and handlers

**Files:**
- Create: `bot/client.py`
- Create: `bot/handlers.py`
- Create: `tests/test_handlers.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_handlers.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import AIMessage


def make_mock_message(content: str, user_id: str = "123456"):
    message = MagicMock()
    message.content = content
    message.author.id = int(user_id)
    message.channel.send = AsyncMock()
    message.channel.typing.return_value.__aenter__ = AsyncMock(return_value=None)
    message.channel.typing.return_value.__aexit__ = AsyncMock(return_value=None)
    return message


@pytest.mark.asyncio
async def test_handle_message_sends_agent_response():
    message = make_mock_message("download Inception")
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(return_value={
        "messages": [AIMessage(content="⏬ Queued Inception (2010)!")]
    })

    with patch("bot.handlers.get_agent", new=AsyncMock(return_value=mock_agent)):
        from bot.handlers import handle_message
        await handle_message(message)

    message.channel.send.assert_called_once_with("⏬ Queued Inception (2010)!")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_handlers.py -v
```

Expected: `ModuleNotFoundError: No module named 'bot.handlers'`

- [ ] **Step 3: Write bot/handlers.py**

```python
# bot/handlers.py
import discord
from langchain_core.messages import HumanMessage
from agent.graph import get_agent


async def handle_message(message: discord.Message) -> None:
    """Route a Discord DM through the LangGraph agent and reply with the response."""
    user_id = str(message.author.id)

    async with message.channel.typing():
        agent = await get_agent(user_id)
        result = await agent.ainvoke(
            {"messages": [HumanMessage(content=message.content)]},
            config={"configurable": {"thread_id": user_id}},
        )
        response: str = result["messages"][-1].content

    await message.channel.send(response)


async def send_completion_notification(
    bot: discord.Client,
    discord_user_id: str,
    movie_title: str,
    movie_year: int,
    movie_id: int,
    file_path: str,
) -> None:
    """DM the user that their download completed, with a movie poster embed."""
    from agent.tools import get_poster_url

    user = await bot.fetch_user(int(discord_user_id))
    poster_url = await get_poster_url(movie_id)

    embed = discord.Embed(
        title=f"✅ {movie_title} ({movie_year})",
        description=f"Download complete!\nSaved to `{file_path}`",
        color=discord.Color.green(),
    )
    if poster_url:
        embed.set_thumbnail(url=poster_url)

    await user.send(embed=embed)


async def send_failure_notification(
    bot: discord.Client,
    discord_user_id: str,
    movie_title: str,
    movie_year: int,
    error: str,
) -> None:
    """DM the user that their download failed."""
    user = await bot.fetch_user(int(discord_user_id))
    await user.send(f"❌ Failed to download **{movie_title} ({movie_year})**: {error}")
```

- [ ] **Step 4: Write bot/client.py**

```python
# bot/client.py
import asyncio
import discord
from bot.handlers import handle_message, send_completion_notification, send_failure_notification
from db.models import DownloadJob
from config import Config


class MovieBot(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self._worker_task: asyncio.Task | None = None

    async def setup_hook(self) -> None:
        from downloader.worker import run_worker
        self._worker_task = self.loop.create_task(run_worker(self._notify))

    async def on_ready(self) -> None:
        print(f"Bot ready as {self.user} (ID: {self.user.id})")

    async def on_message(self, message: discord.Message) -> None:
        if message.author == self.user:
            return
        if isinstance(message.channel, discord.DMChannel):
            await handle_message(message)

    async def _notify(
        self, job: DownloadJob, file_path: str | None, error: str | None = None
    ) -> None:
        if error:
            await send_failure_notification(
                self, job.discord_user_id, job.movie_title, job.movie_year, error
            )
        else:
            await send_completion_notification(
                self, job.discord_user_id, job.movie_title, job.movie_year, job.movie_id, file_path
            )


bot = MovieBot()
```

- [ ] **Step 5: Run test to verify it passes**

```bash
pytest tests/test_handlers.py -v
```

Expected: `1 passed`

- [ ] **Step 6: Commit**

```bash
git add bot/ tests/test_handlers.py
git commit -m "feat: add Discord bot client, message handlers, and download notifications"
```

---

## Task 11: Main entry point and DB init script

**Files:**
- Create: `main.py`
- Create: `scripts/init_db.py`
- Create: `.env.example`

- [ ] **Step 1: Write main.py**

```python
# main.py
import asyncio
from bot.client import bot
from db.queue import init_db
from config import Config


async def main() -> None:
    Config.validate()
    await init_db()
    async with bot:
        await bot.start(Config.DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Write scripts/init_db.py**

```python
# scripts/init_db.py
"""Run once to initialize the PostgreSQL database schema."""
import asyncio
from db.queue import init_db
from config import Config


async def main() -> None:
    Config.validate()
    await init_db()
    print("Database initialized successfully.")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 3: Write .env.example**

```bash
cat > .env.example << 'EOF'
GROQ_API_KEY=your_groq_api_key
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_USER_ID=your_discord_user_id
DATABASE_URL=postgresql://user:password@localhost:5432/yts_bot
DOWNLOAD_PATH=/path/to/your/Movies
OPENSUBTITLES_USERNAME=your_opensubtitles_username
OPENSUBTITLES_PASSWORD=your_opensubtitles_password
WORKER_POLL_INTERVAL=5
EOF
```

- [ ] **Step 4: Run the full test suite**

```bash
pytest tests/ -v
```

Expected: all tests pass

- [ ] **Step 5: Commit**

```bash
git add main.py scripts/init_db.py .env.example
git commit -m "feat: add main entry point, DB init script, and .env.example"
```

---

## Self-Review

**Spec coverage:**
- Discord as primary interface ✅ Task 10
- LangGraph + Groq agent ✅ Task 6
- PostgreSQL for agent memory + queue ✅ Tasks 2, 6
- YTS search + movie details ✅ Task 4
- Smart quality selection ✅ Task 3
- Ambiguity handling ✅ Task 6 (system prompt)
- Duplicate detection ✅ Task 5
- Download queue (status, cancel) ✅ Task 5
- libtorrent download ✅ Task 7
- Download worker with progress ✅ Task 8
- Plex-ready folder structure ✅ Task 8
- Subtitle download ✅ Task 9
- Discord notifications on completion (with poster) ✅ Task 10
- All env vars documented ✅ Task 1, Task 11

**Type consistency check:**
- `update_job(job_id, **kwargs)` defined in `db/queue.py`, called in `downloader/worker.py` ✅
- `cancel_job_by_title(movie_title)` defined in `db/queue.py`, called in `agent/tools.py` ✅
- `build_queue_tools(discord_user_id)` defined in `agent/tools.py`, called in `agent/graph.py` ✅
- `get_poster_url(movie_id)` defined in `agent/tools.py`, called in `bot/handlers.py` ✅
- `download_subtitles(file_path, title, year)` defined in `downloader/subtitles.py`, called in `downloader/worker.py` ✅
- `download_torrent(url, save_path, callback)` defined in `downloader/torrent.py`, called in `downloader/worker.py` ✅
- `DownloadJob` model fields match all usage sites ✅
