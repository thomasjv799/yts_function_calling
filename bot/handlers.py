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
