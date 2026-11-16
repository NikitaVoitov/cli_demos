## About

An AI agent in Splunk doesn't need a framework or a packaged app to get started. With the Splunk Agentic SDK, a short Python script connects to Splunk, gives a model a handful of tools, and returns an answer your code can use.

In this demo you ask Cursor CLI for that script. It writes `agent.py`, runs it, and the agent answers a real question about the checkout logs: which index holds them, and how many events it has. Then you run the same script yourself, with no Cursor involved.

The script does four things. It connects to Splunk, picks a Gemini model on Vertex AI, allowlists two Splunk MCP Server tools (`splunk_get_indexes` and `splunk_run_query`), and sets an output schema so the answer comes back as typed data instead of prose. The model can't call any other tool, and the SDK's default limits on time, steps, and tokens stay on.

### Prerequisites

- **Splunk Cloud** stack with the Splunk MCP Server app, REST port 8089 reachable, and a token
- **Splunk Agentic SDK** (`splunk-sdk` 3.0 or later, with the `google` extra for Gemini)
- **A model**: Gemini on Vertex AI here, or OpenAI, Anthropic, or Ollama by swapping one class
- **Cursor CLI**, only if you want it to write the script for you

### Setup notes for this recording

The SDK is built for apps that run inside Splunk, and two details show when you run it from a plain script. Neither changes what the script does.

- The SDK looks for its own folder under `$SPLUNK_HOME/etc/apps/<app>/`, so the recording environment installs it there.
- SDK 3.0.1 asks for the MCP token with a call that this stack's MCP Server doesn't accept, so a small `sitecustomize.py` hands it the stack's existing MCP token.

### Learn more

- [Splunk SDK for Python on GitHub](https://github.com/splunk/splunk-sdk-python)
- [Agentic Splunk SDK guide](https://github.com/splunk/splunk-sdk-python/blob/develop/splunklib/ai/README.md)
- [Splunk MCP Server on Splunkbase](https://splunkbase.splunk.com/app/7931)
