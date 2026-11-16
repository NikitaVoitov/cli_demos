import asyncio
import os
from urllib.parse import urlparse

from pydantic import BaseModel
from splunklib.ai import Agent, GoogleModel
from splunklib.ai.messages import HumanMessage
from splunklib.ai.tool_settings import RemoteToolSettings, ToolAllowlist, ToolSettings
from splunklib.client import connect


class CheckoutLogs(BaseModel):
    index: str
    event_count: int


async def main() -> None:
    host = urlparse(os.environ["SPLUNK_HOST"])
    service = connect(scheme=host.scheme, host=host.hostname, port=host.port or 8089,
                      splunkToken=os.environ["SPLUNK_TOKEN"], autologin=True, verify=False)
    model = GoogleModel(model="gemini-3.5-flash", project=os.environ["GOOGLE_CLOUD_PROJECT"],
                        location=os.environ["GOOGLE_CLOUD_LOCATION"])
    tools = ToolSettings(local=False, remote=RemoteToolSettings(
        allowlist=ToolAllowlist(names=["splunk_get_indexes", "splunk_run_query"])))
    question = (
        "Which index holds our checkout request logs, and how many events does it have? "
        "List indexes with splunk_get_indexes, then count that index over all time "
        "with splunk_run_query (earliest_time=0, latest_time=now, app=search)."
    )
    async with Agent(
        model=model, service=service, tool_settings=tools, output_schema=CheckoutLogs,
        system_prompt="Use only the allowlisted Splunk tools, then return the index and event count.",
    ) as agent:
        result = await agent.invoke([HumanMessage(content=question)])
    print(result.structured_output.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
