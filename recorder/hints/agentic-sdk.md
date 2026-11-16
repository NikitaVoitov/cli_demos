## Splunk Agentic SDK (`splunklib.ai`)

The SDK is already installed. Run scripts with plain `python3`; do not install packages, create a virtual environment, or read the SDK's source. Settings come from the environment, so never hardcode or print them: `SPLUNK_HOST` (a URL such as `https://<stack>:8089`), `SPLUNK_TOKEN`, `GOOGLE_CLOUD_PROJECT`, and `GOOGLE_CLOUD_LOCATION`.

The pieces you need:

```python
from splunklib.client import connect
from splunklib.ai import Agent, GoogleModel
from splunklib.ai.messages import HumanMessage
from splunklib.ai.tool_settings import RemoteToolSettings, ToolAllowlist, ToolSettings

service = connect(scheme="https", host=<hostname>, port=8089, splunkToken=<token>, autologin=True, verify=False)
model = GoogleModel(model="gemini-3.5-flash", project=<project>, location=<location>)  # Gemini on Vertex AI
tools = ToolSettings(local=False, remote=RemoteToolSettings(allowlist=ToolAllowlist(names=["<mcp tool>", ...])))

async with Agent(model=model, system_prompt="...", service=service, tool_settings=tools, output_schema=<pydantic model>) as agent:
    result = await agent.invoke([HumanMessage(content="...")])
    result.structured_output          # an instance of the output schema
```

`verify=False` is needed because this stack's certificate authority is not in the system trust store. Remote tools are the Splunk MCP Server tools, and only the allowlisted ones reach the model. Leave the default limits as they are. Keep the script short and print the structured output as JSON (`model_dump_json(indent=2)`).
