from datetime import datetime, timezone

from chatchat.server.pydantic_v1 import Field

from langchain_chatchat.agent_toolkits.all_tools.tool import BaseToolOutput
from .tools_registry import regist_tool


@regist_tool(title="当前时间")
def system_time(
    fmt: str = Field("iso", description="output format, iso or unix"),
):
    """Return the current UTC time."""
    now = datetime.now(timezone.utc)
    if fmt == "unix":
        return BaseToolOutput(int(now.timestamp()))
    return BaseToolOutput(now.isoformat(timespec="seconds"))