"""Optional F09 browser fixture server; separate ports, temporary SQLite and media only."""

import argparse
import os
import sys
from pathlib import Path

# Global backend engines are constructed on import. Point unused defaults at a closed
# loopback port; isolated_api replaces every database and quota dependency before serving.
os.environ["DATABASE_URL"] = "mysql+pymysql://unused:unused@127.0.0.1:1/unused"
os.environ["APP_ENV"] = "development"
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

import uvicorn  # noqa: E402
from isolated_api import isolated_api  # noqa: E402


def port(value):
    number = int(value)
    if not 1024 <= number <= 65535:
        raise argparse.ArgumentTypeError("Use an unprivileged port from 1024 to 65535.")
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=port, default=8011)
    parser.add_argument("--frontend-port", type=port, default=5180)
    args = parser.parse_args()
    with isolated_api(args.frontend_port, base_domain="f09.localhost") as app:
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=args.port,
            proxy_headers=False,
            access_log=False,
            log_level="warning",
        )


if __name__ == "__main__":
    main()
