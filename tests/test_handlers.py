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
