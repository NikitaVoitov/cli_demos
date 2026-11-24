#!/usr/bin/env python3
"""A local OpenAI-compatible model for Copilot CLI dry runs of the capture: no Copilot service, no real model.

    python3 scripts/copilot_fake_model.py [--port 8765] [--command 'jpterm execute hunt.ipynb --cell raw-search']
    COPILOT_OFFLINE=true COPILOT_PROVIDER_BASE_URL=http://127.0.0.1:8765/v1 COPILOT_MODEL=gpt-5.4 \\
      COPILOT_PROVIDER_WIRE_API=completions .captures/venv/bin/python -m pipeline.capture <scenario> <take>

Every prompt gets the same answer: one bash tool call running --command, then a one-line reply once the result is
back. Each answer waits 4 s, so the driver sees the client working. Standard library only; never publish such a take.
"""

import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def handler(command: str):
    class Model(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            body = json.dumps({"data": [{"id": "gpt-5.4", "object": "model"}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            messages = json.loads(self.rfile.read(int(self.headers["Content-Length"]))).get("messages", [])
            time.sleep(4)
            if messages and messages[-1]["role"] == "tool":
                delta, finish = {"role": "assistant", "content": "Done. That is the command's result."}, "stop"
            else:
                call = {"command": command, "description": "Run the dry-run command", "mode": "sync", "initial_wait": 60}
                delta = {"role": "assistant", "tool_calls": [{"index": 0, "id": "call_1", "type": "function",
                                                              "function": {"name": "bash", "arguments": json.dumps(call)}}]}
                finish = "tool_calls"
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for choice in ({"index": 0, "delta": delta}, {"index": 0, "delta": {}, "finish_reason": finish}):
                chunk = {"id": "fake", "object": "chat.completion.chunk", "model": "gpt-5.4", "choices": [choice]}
                self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
                self.wfile.flush()
            self.wfile.write(b"data: [DONE]\n\n")

    return Model


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--command", default="echo hello from the fake model")
    args = parser.parse_args()
    print(f"fake model on http://127.0.0.1:{args.port}/v1")
    ThreadingHTTPServer(("127.0.0.1", args.port), handler(args.command)).serve_forever()
