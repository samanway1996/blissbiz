import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from pydantic import ValidationError
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.core.config import Settings
from app.main import create_app


@pytest.mark.parametrize(
    "trusted,peer,expected",
    [
        ([], "127.0.0.1", "127.0.0.1"),
        (["127.0.0.1/32"], "127.0.0.1", "198.51.100.7"),
        (["127.0.0.1/32"], "198.51.100.8", "198.51.100.8"),
        (["10.10.0.0/24"], "10.10.0.2", "198.51.100.7"),
    ],
)
def test_only_trusted_proxy_changes_client_identity(trusted, peer, expected):
    app = FastAPI()
    config = Settings(_env_file=None, database_url="sqlite://", trusted_proxy_ips=trusted)
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=config.trusted_proxy_ips)

    @app.get("/identity")
    def identity(request: Request):
        return {
            "peer": request.client.host,
            "scheme": request.url.scheme,
            "host": request.url.hostname,
        }

    with TestClient(app, client=(peer, 1234)) as client:
        response = client.get(
            "/identity",
            headers={
                "X-Forwarded-For": "198.51.100.7",
                "X-Forwarded-Proto": "https",
                "X-Forwarded-Host": "evil.example.com",
            },
        )
    assert response.json() == {
        "peer": expected,
        "scheme": "https" if expected == "198.51.100.7" else "http",
        "host": "testserver",
    }


@pytest.mark.parametrize("values", [["*"], ["0.0.0.0/0"], ["::/0"], ["proxy.example.com"]])
def test_proxy_config_rejects_unrestricted_or_non_ip_trust(values):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url="sqlite://", trusted_proxy_ips=values)


def test_production_hides_interactive_docs():
    config = Settings(
        _env_file=None,
        database_url="sqlite://",
        app_env="production",
        storefront_base_url="https://example.com",
        admin_base_url="https://admin.example.com",
        auth_allowed_origins=["https://admin.example.com"],
        upload_dir="/var/lib/blissbiz/uploads",
    )
    with TestClient(create_app(config), base_url="https://admin.example.com") as client:
        assert client.get("/api/docs").status_code == 404
        assert client.get("/api/openapi.json").status_code == 404
