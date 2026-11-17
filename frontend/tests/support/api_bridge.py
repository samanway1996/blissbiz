"""JSON-line transport for Node tests; never binds a port or connects to the local DB."""

import base64
import json
import sys
from contextlib import ExitStack
from urllib.parse import urlsplit

from fastapi.testclient import TestClient
from isolated_api import isolated_api


def main():
    with isolated_api() as app, ExitStack() as stack:
        clients = {}
        for line in sys.stdin:
            request = json.loads(line)
            assert request["url"].startswith(("/api/", "/media/"))
            origin = request.get("origin", "http://admin.localhost:5173")
            parsed = urlsplit(origin)
            assert parsed.scheme == "http" and parsed.port == 5173
            assert parsed.hostname == "localhost" or parsed.hostname.endswith(".localhost")
            browser = request.get("browser", "default")
            if browser not in clients:
                clients[browser] = stack.enter_context(TestClient(app))
            headers = {**request["headers"], "Origin": origin}
            if request.get("credentials") == "omit":
                headers["Cookie"] = ""
            content = request.get("body")
            if request.get("base64"):
                content = base64.b64decode(content)
            response = clients[browser].request(
                request["method"], f"{origin}{request['url']}", content=content, headers=headers
            )
            binary = not response.headers.get("Content-Type", "").startswith("application/json")
            print(
                json.dumps(
                    {
                        "status": response.status_code,
                        "body": base64.b64encode(response.content).decode()
                        if binary
                        else response.text,
                        "base64": binary,
                        "headers": {
                            "Content-Type": response.headers.get("Content-Type", ""),
                            "Retry-After": response.headers.get("Retry-After", ""),
                        },
                    }
                ),
                flush=True,
            )


if __name__ == "__main__":
    main()
