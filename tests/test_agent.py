import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver


@pytest.mark.asyncio
async def test_get_agent_returns_runnable():
    mock_pool = MagicMock()
    mock_pool.open = AsyncMock()

    mock_checkpointer = MagicMock(spec=AsyncPostgresSaver)
    mock_checkpointer.setup = AsyncMock()

    with patch("agent.graph.AsyncConnectionPool", return_value=mock_pool), \
         patch("agent.graph.AsyncPostgresSaver", return_value=mock_checkpointer):
        from agent.graph import get_agent
        agent = await get_agent("123456")
        assert agent is not None
        assert hasattr(agent, "ainvoke")
