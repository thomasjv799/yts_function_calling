import logging
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_groq import ChatGroq
from psycopg_pool import AsyncConnectionPool
from agent.tools import search_movies, get_movie_details, build_queue_tools
from config import Config

logger = logging.getLogger(__name__)

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
        logger.info("Initialising Postgres connection pool for LangGraph checkpointer...")
        _pool = AsyncConnectionPool(
            conninfo=Config.DATABASE_URL,
            max_size=10,
            open=False,
            kwargs={"autocommit": True, "prepare_threshold": 0},
        )
        await _pool.open()
        _checkpointer = AsyncPostgresSaver(_pool)
        await _checkpointer.setup()
        logger.info("LangGraph checkpointer ready.")
    return _checkpointer


async def clear_thread(discord_user_id: str) -> None:
    """Delete all LangGraph checkpoint state for a user's conversation thread."""
    global _pool
    if _pool is None:
        logger.warning("Cannot clear thread for %s — pool not initialised", discord_user_id)
        return
    logger.info("Clearing corrupted checkpoint thread for user %s", discord_user_id)
    async with _pool.connection() as conn:
        for table in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
            await conn.execute(f"DELETE FROM {table} WHERE thread_id = %s", (discord_user_id,))
    logger.info("Checkpoint thread cleared for user %s", discord_user_id)


async def get_agent(discord_user_id: str):
    """Create a ReAct agent for the given Discord user backed by the shared Postgres checkpointer."""
    logger.debug("Building agent for user %s", discord_user_id)
    checkpointer = await _get_checkpointer()
    llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=Config.GROQ_API_KEY)
    tools = [search_movies, get_movie_details] + build_queue_tools(discord_user_id)

    return create_react_agent(
        llm,
        tools,
        checkpointer=checkpointer,
        prompt=SYSTEM_PROMPT,
    )
