"""Run with backend/.venv/bin/python3 scripts/test_deployment.py after the Vue build.

Use --vps to build and exercise the VPS images instead of a prebuilt local frontend.

Owns and removes only a freshly generated Compose project and disposable test volumes.
"""

import argparse
import hashlib
import io
import json
import os
import re
import secrets
import shutil
import socket
import ssl
import subprocess
import tempfile
import time
from pathlib import Path
from uuid import uuid4

import httpx
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--vps", action="store_true", help="Exercise the actual VPS Compose/images."
    )
    vps = parser.parse_args().vps
    docker = shutil.which("docker") or str(Path.home() / ".rd/bin/docker")
    if not Path(docker).exists() or (not vps and not (ROOT / "frontend/dist/index.html").exists()):
        raise SystemExit("Docker and a built frontend are required. Run make check first.")
    project = f"blissbiz-test-{uuid4().hex[:12]}"
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    network = f"10.251.{secrets.randbelow(250) + 1}"
    domain = "blissbiz.biz" if vps else "blissbiz.test"
    port_suffix = "" if vps else f":{port}"
    login_limit = 20 if vps else 5
    with tempfile.TemporaryDirectory(prefix="blissbiz-deploy-") as temporary:
        files = Path(temporary)
        env = {
            **os.environ,
            "COMPOSE_FILE": str(ROOT / "deploy/compose.test.yaml"),
            "COMPOSE_PROJECT_NAME": project,
            "TEST_FILES": str(files),
            "TEST_DB_PASSWORD": secrets.token_hex(20),
            "TEST_ROOT_PASSWORD": secrets.token_hex(20),
            "TEST_HTTPS_PORT": str(port),
            "TEST_SUBNET": f"{network}.0/24",
            "TEST_PROXY_IP": f"{network}.10",
        }
        env["PATH"] = str(Path(docker).parent) + os.pathsep + env.get("PATH", "")
        if vps:
            with socket.socket() as http_probe:
                http_probe.bind(("127.0.0.1", 0))
                http_port = http_probe.getsockname()[1]
            env.update(
                {
                    "COMPOSE_FILE": str(ROOT / "deploy/compose.vps.yaml"),
                    "MYSQL_PASSWORD": env["TEST_DB_PASSWORD"],
                    "MYSQL_ROOT_PASSWORD": env["TEST_ROOT_PASSWORD"],
                    "BIND_ADDRESS": "127.0.0.1",
                    "HTTP_PORT": str(http_port),
                    "HTTPS_PORT": str(port),
                    "NETWORK_SUBNET": env["TEST_SUBNET"],
                    "PROXY_IP": env["TEST_PROXY_IP"],
                    "TLS_DIR": str(files),
                    "RELEASE_TAG": project,
                    "PYTHON_IMAGE": os.environ.get("TEST_PYTHON_IMAGE", "python:3.13-slim"),
                    "NGINX_IMAGE": os.environ.get("TEST_NGINX_IMAGE", "nginx:stable-alpine"),
                    "NODE_IMAGE": os.environ.get("TEST_NODE_IMAGE", "node:24-alpine"),
                    "MYSQL_IMAGE": os.environ.get("TEST_MYSQL_IMAGE", "mysql:8.4"),
                }
            )

        def compose(*args, capture=False, input=None):
            return subprocess.run(
                [docker, "compose", *args],
                env=env,
                cwd=ROOT,
                input=input,
                check=True,
                stdout=subprocess.PIPE if capture else None,
                stderr=subprocess.PIPE if capture else None,
            )

        subprocess.run(
            [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-nodes",
                "-days",
                "1",
                "-keyout",
                str(files / "key.pem"),
                "-out",
                str(files / "cert.pem"),
                "-subj",
                f"/CN={domain}",
                "-addext",
                f"subjectAltName=DNS:{domain},DNS:*.{domain}",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        site = (ROOT / "deploy/nginx/site.conf").read_text().replace("example.com", "blissbiz.test")
        site = site.replace(r"example\.com", r"blissbiz\.test")
        site = site.replace("/etc/letsencrypt/live/blissbiz.test/fullchain.pem", "/tls/cert.pem")
        site = site.replace("/etc/letsencrypt/live/blissbiz.test/privkey.pem", "/tls/key.pem")
        (files / "site.conf").write_text(site)
        (files / "proxy.conf").write_text(
            (ROOT / "deploy/nginx/proxy.conf").read_text().replace("127.0.0.1:8000", "backend:8000")
        )
        if vps:
            shutil.copyfile(files / "cert.pem", files / "fullchain.pem")
            shutil.copyfile(files / "key.pem", files / "privkey.pem")
        original_dns = socket.getaddrinfo

        def local_dns(host, *args, **kwargs):
            if isinstance(host, bytes):
                host = host.decode()
            if host.endswith(f".{domain}") or host == domain:
                host = "127.0.0.1"
                if vps and args and args[0] == 443:
                    args = (port, *args[1:])
            return original_dns(host, *args, **kwargs)

        try:
            if vps:
                compose("build", "backend", "proxy")
                compose("up", "-d", "--wait", "--wait-timeout", "240", "db")
                compose("run", "--rm", "--no-deps", "migrate")
            compose("up", "-d", "--wait", "--wait-timeout", "240", *([] if vps else ["--build"]))
            if vps:
                for service in ("db", "backend"):
                    container_id = (
                        compose("ps", "-q", service, capture=True).stdout.decode().strip()
                    )
                    bindings = subprocess.check_output(
                        [
                            docker,
                            "inspect",
                            "--format",
                            "{{json .HostConfig.PortBindings}}",
                            container_id,
                        ],
                        env=env,
                    )
                    assert not json.loads(bindings), f"{service} has published ports"
            compose("exec", "-T", "proxy", "nginx", "-t")
            socket.getaddrinfo = local_dns
            tls = ssl.create_default_context(cafile=str(files / "cert.pem"))
            admin = f"https://admin.{domain}{port_suffix}"
            with httpx.Client(base_url=admin, verify=tls, trust_env=False, timeout=30) as owner:
                # Port forwarding can become ready slightly after Compose reports Running.
                for _ in range(60):
                    try:
                        if owner.get("/api/ready").status_code == 200:
                            break
                    except httpx.ConnectError:
                        pass
                    time.sleep(0.25)
                else:
                    raise AssertionError("HTTPS proxy did not become reachable.")
                assert owner.get("/api/ready").status_code == 200
                assert owner.get("/api/docs").status_code == 404
                assert owner.get("/businesses/example/deep-link").status_code == 200
                if vps:
                    html = owner.get("/login").text
                    scripts = re.findall(r'(?:src|href)="(/assets/[^\"]+\.js)"', html)
                    assert scripts, "Built frontend has no script assets"
                    asset_root = "/opt/blissbiz/current/frontend/dist"
                    # Vite also emits lazy-loaded chunks, including the app's origin settings.
                    paths = (
                        compose(
                            "exec",
                            "-T",
                            "proxy",
                            "find",
                            f"{asset_root}/assets",
                            "-type",
                            "f",
                            "-name",
                            "*.js",
                            capture=True,
                        )
                        .stdout.decode()
                        .splitlines()
                    )
                    scripts.extend(path.removeprefix(asset_root) for path in paths)
                    bundles = []
                    for asset in scripts:
                        response = owner.get(asset)
                        assert response.status_code == 200
                        assert "javascript" in response.headers["content-type"]
                        bundles.append(response.text)
                    assert "https://admin.blissbiz.biz" in "".join(bundles)

                def csrf(client=owner):
                    response = client.get("/api/v1/auth/csrf")
                    assert response.status_code == 200
                    assert (
                        "Secure" in response.headers["set-cookie"]
                        and "HttpOnly" in response.headers["set-cookie"]
                    )
                    assert "Domain=" not in response.headers["set-cookie"]
                    return {
                        "Origin": admin,
                        "X-CSRF-Token": response.json()["csrf_token"],
                    }

                credentials = {
                    "email": f"{uuid4().hex}@example.com",
                    "password": "a long deployment test passphrase",
                }
                response = owner.post(
                    "/api/v1/registrations",
                    headers=csrf(),
                    json={
                        "owner": {"full_name": "Deployment test owner", **credentials},
                        "business": {"name": "Deployment Bakery", "slug": "bakery"},
                    },
                )
                assert response.status_code == 201, response.status_code
                base = f"/api/v1/admin/businesses/{response.json()['business']['id']}"
                headers = csrf()
                response = owner.post(
                    f"{base}/products",
                    headers=headers,
                    json={"name": "Cake", "price": "499.00"},
                )
                assert response.status_code == 201
                product = f"{base}/products/{response.json()['id']}"
                image = io.BytesIO()
                Image.new("RGB", (8, 8), "red").save(image, format="PNG")
                response = owner.put(
                    f"{product}/image",
                    headers=headers,
                    files={"file": ("cake.png", image.getvalue(), "image/png")},
                )
                assert response.status_code == 200
                image_url = response.json()["image_url"]
                with httpx.Client(
                    base_url=admin, verify=tls, trust_env=False, timeout=30
                ) as second_owner:
                    second = second_owner.post(
                        "/api/v1/registrations",
                        headers=csrf(second_owner),
                        json={
                            "owner": {
                                "full_name": "Second Owner",
                                "email": f"{uuid4().hex}@example.com",
                                "password": credentials["password"],
                            },
                            "business": {"name": "Book Shop", "slug": "books"},
                        },
                    )
                    assert second.status_code == 201
                    second_base = f"/api/v1/admin/businesses/{second.json()['business']['id']}"
                    second_headers = csrf(second_owner)
                    second_product = second_owner.post(
                        f"{second_base}/products",
                        headers=second_headers,
                        json={"name": "Book", "price": "99.00"},
                    )
                    assert second_product.status_code == 201
                    second_id = second_product.json()["id"]
                    assert (
                        second_owner.patch(
                            f"{second_base}/products/{second_id}",
                            headers=second_headers,
                            json={"status": "published"},
                        ).status_code
                        == 200
                    )
                    assert owner.get(second_base).status_code == 404
                    assert second_owner.get(base).status_code == 404
                with httpx.Client(
                    base_url=f"https://bakery.{domain}{port_suffix}",
                    verify=tls,
                    trust_env=False,
                    timeout=30,
                ) as customer:
                    assert customer.get("/api/v1/storefront").json()["slug"] == "bakery"
                    assert customer.get("/api/v1/storefront/products").json()["total"] == 0
                    assert customer.get(image_url).status_code == 200
                    assert not customer.cookies
                    assert (
                        customer.get(f"/api/v1/storefront/products/{second_id}").status_code == 404
                    )
                    with httpx.Client(
                        base_url=f"https://books.{domain}{port_suffix}",
                        verify=tls,
                        trust_env=False,
                    ) as books:
                        assert books.get("/api/v1/storefront/products").json()["total"] == 1
                        assert (
                            books.get(
                                f"/api/v1/storefront/products/{product.rsplit('/', 1)[-1]}"
                            ).status_code
                            == 404
                        )
                    assert (
                        owner.patch(
                            product, headers=headers, json={"status": "published"}
                        ).status_code
                        == 200
                    )
                    assert customer.get("/api/v1/storefront/products").json()["total"] == 1
                    assert (
                        customer.get(
                            "/api/v1/storefront",
                            headers={"X-Forwarded-Host": "evil.example.com"},
                        ).json()["slug"]
                        == "bakery"
                    )
                    assert (
                        owner.patch(product, headers=headers, json={"status": "draft"}).status_code
                        == 200
                    )
                    assert customer.get("/api/v1/storefront/products").json()["total"] == 0
                assert owner.post("/api/v1/auth/logout", headers=headers).status_code == 204
                assert (
                    owner.post("/api/v1/auth/login", headers=csrf(), json=credentials).status_code
                    == 200
                )
                assert owner.post("/api/v1/auth/logout", headers=csrf()).status_code == 204
                headers = csrf()
                for attempt in range(login_limit - 1):
                    result = owner.post(
                        "/api/v1/auth/login",
                        headers={
                            **headers,
                            "X-Forwarded-For": f"198.51.100.{attempt + 1}",
                        },
                        json={
                            "email": f"missing-{attempt}@example.com",
                            "password": "wrong",
                        },
                    )
                    assert result.status_code == 401
                assert (
                    owner.post("/api/v1/auth/login", headers=headers, json=credentials).status_code
                    == 429
                )
                with httpx.Client(verify=tls, trust_env=False) as public_client:
                    assert (
                        public_client.get(
                            f"https://unknown.{domain}{port_suffix}/api/v1/storefront"
                        ).status_code
                        == 404
                    )
                print(
                    "HTTPS/Nginx, secure cookies, tenant routing, publication, media, "
                    "CSRF/login and shared quotas passed.",
                    flush=True,
                )

            compose("restart", "backend")
            for _ in range(40):
                try:
                    with httpx.Client(
                        base_url=admin, verify=tls, trust_env=False, timeout=5
                    ) as client:
                        if client.get(image_url).status_code == 200:
                            break
                except httpx.HTTPError:
                    pass
                time.sleep(0.5)
            else:
                raise AssertionError("Media did not survive backend restart.")

            compose("stop", "backend")
            upload_copy = files / "upload-copy"
            upload_copy.mkdir()
            compose("cp", "backend:/data/uploads/.", str(upload_copy))
            backup = files / "backup"
            subprocess.run(
                [
                    "sh",
                    str(ROOT / "scripts/backup.sh"),
                    "--writes-paused",
                    str(upload_copy),
                    str(backup),
                ],
                env=env,
                cwd=ROOT,
                check=True,
            )
            for name in ("database.sql", "uploads.tar.gz"):
                assert (
                    hashlib.sha256((backup / name).read_bytes()).hexdigest()
                    in (backup / "SHA256SUMS").read_text()
                )
            compose(
                "exec",
                "-T",
                "db",
                "sh",
                "-c",
                'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot',
                input=b"CREATE DATABASE restore_test;\n",
            )
            compose(
                "exec",
                "-T",
                "db",
                "sh",
                "-c",
                'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot restore_test',
                input=(backup / "database.sql").read_bytes(),
            )
            count = compose(
                "exec",
                "-T",
                "db",
                "sh",
                "-c",
                'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot -N restore_test '
                '-e "SELECT COUNT(*) FROM products"',
                capture=True,
            ).stdout.strip()
            assert count == b"2"
            restored = files / "restored-uploads"
            restored.mkdir()
            subprocess.run(
                ["tar", "-xzf", str(backup / "uploads.tar.gz"), "-C", str(restored)],
                check=True,
            )
            assert len(list(restored.rglob("*.png"))) == 1
            print(
                "Restart persistence and checksummed MySQL/image backup "
                "+ disposable restore passed.",
                flush=True,
            )
        finally:
            socket.getaddrinfo = original_dns
            compose("down", "--volumes", "--remove-orphans")


if __name__ == "__main__":
    main()
