# bot/handlers.py
import logging
import discord
from langchain_core.messages import HumanMessage
from agent.graph import get_agent, clear_thread

logger = logging.getLogger(__name__)


async def handle_message(message: discord.Message) -> None:
    """Route a Discord DM through the LangGraph agent and reply with the response."""
    user_id = str(message.author.id)
    logger.info("Message from %s: %r", user_id, message.content[:100])

    try:
        async with message.channel.typing():
            logger.debug("Initialising agent for user %s", user_id)
            agent = await get_agent(user_id)

            logger.debug("Invoking agent for user %s", user_id)
            result = await agent.ainvoke(
                {"messages": [HumanMessage(content=message.content)]},
                config={"configurable": {"thread_id": user_id}},
            )
            response: str = result["messages"][-1].content
            logger.info("Agent response for %s: %r", user_id, response[:200])

        await message.channel.send(response)

    except ValueError as e:
        if "INVALID_CHAT_HISTORY" in str(e):
            logger.warning("Corrupted chat history for user %s — clearing thread", user_id)
            await clear_thread(user_id)
            await message.channel.send(
                "Your conversation history got into a bad state and has been reset. "
                "Please send your message again."
            )
        else:
            logger.exception("Agent ValueError for user %s", user_id)
            await message.channel.send("Something went wrong on my end. Check the logs.")
    except Exception:
        logger.exception("Agent error handling message from %s", user_id)
        await message.channel.send(
            "Something went wrong on my end. Check the logs."
        )


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

    logger.info("Sending completion notification to %s for %s (%s)", discord_user_id, movie_title, movie_year)
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
    logger.warning("Sending failure notification to %s for %s (%s): %s", discord_user_id, movie_title, movie_year, error)
    user = await bot.fetch_user(int(discord_user_id))
    await user.send(f"❌ Failed to download **{movie_title} ({movie_year})**: {error}")
