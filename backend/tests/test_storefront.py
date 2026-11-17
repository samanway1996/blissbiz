from decimal import Decimal

import pytest

from app.db.models import Product


@pytest.fixture
def storefront(catalog_context):
    c = catalog_context
    products = [
        Product(
            business_id=c.business.id,
            name="Cake 100%",
            description="Chocolate",
            price=Decimal("49.90"),
            status="published",
        ),
        Product(business_id=c.business.id, name="Secret Cake", price=Decimal("1.00")),
        Product(
            business_id=c.foreign.id, name="Other Cake", price=Decimal("2.00"), status="published"
        ),
    ]
    c.db.add_all(products)
    c.db.commit()
    c.published, c.draft, c.other = products
    c.host = f"{c.business.slug}.localhost:8000"
    c.client.cookies.clear()
    return c


def test_public_profile_contains_only_public_fields(storefront):
    c = storefront
    response = c.client.get("/api/v1/storefront", headers={"Host": c.host})
    assert response.status_code == 200
    assert set(response.json()) == {
        "name",
        "slug",
        "description",
        "contact_email",
        "contact_phone",
        "address",
        "currency",
        "logo_url",
    }
    assert response.json()["slug"] == c.business.slug
    assert response.headers["cache-control"] == "no-store"
    assert "set-cookie" not in response.headers


def test_public_products_exclude_drafts_and_other_tenants(storefront):
    c = storefront
    response = c.client.get(
        "/api/v1/storefront/products",
        headers={"Host": c.host},
        params={"status": "draft", "business_id": c.foreign.id, "q": "CAKE", "page_size": 1},
    )
    assert response.status_code == 200 and response.json()["total"] == 1
    item = response.json()["items"][0]
    assert set(item) == {"id", "name", "description", "price", "image_url"}
    assert item["id"] == c.published.id and item["price"] == "49.90"
    assert (
        c.client.get(
            f"/api/v1/storefront/products/{c.published.id}", headers={"Host": c.host}
        ).json()
        == item
    )
    for product_id in [c.draft.id, c.other.id, "unknown"]:
        assert (
            c.client.get(
                f"/api/v1/storefront/products/{product_id}", headers={"Host": c.host}
            ).status_code
            == 404
        )
    other_host = f"{c.foreign.slug}.localhost:5173"
    other = c.client.get("/api/v1/storefront/products", headers={"Host": other_host}).json()
    assert [item["id"] for item in other["items"]] == [c.other.id]


def test_publication_and_deletion_are_visible_immediately(storefront):
    c = storefront
    c.draft.status = "published"
    c.db.commit()
    assert (
        c.client.get("/api/v1/storefront/products", headers={"Host": c.host}).json()["total"] == 2
    )
    c.published.status = "draft"
    c.db.commit()
    assert (
        c.client.get(
            f"/api/v1/storefront/products/{c.published.id}", headers={"Host": c.host}
        ).status_code
        == 404
    )
    c.db.delete(c.draft)
    c.db.commit()
    assert (
        c.client.get("/api/v1/storefront/products", headers={"Host": c.host}).json()["total"] == 0
    )


def test_forwarded_and_tenant_headers_cannot_change_storefront(storefront):
    c = storefront
    response = c.client.get(
        "/api/v1/storefront",
        headers={
            "Host": c.host,
            "X-Forwarded-Host": f"{c.foreign.slug}.localhost",
            "X-Business-ID": c.foreign.id,
            "Forwarded": f'host="{c.foreign.slug}.localhost"',
        },
    )
    assert response.json()["slug"] == c.business.slug


@pytest.mark.parametrize(
    "host",
    [
        "localhost",
        "admin.localhost",
        "unknown.localhost",
        "api.localhost",
        "shop.localhost.evil.com",
        "shop.evil.com",
        "a.b.localhost",
        "-bad.localhost",
        "bad_.localhost",
        "shop.localhost.",
        "shop.localhost:0",
        "shop.localhost:65536",
        "shop.localhost:abc",
        "user@shop.localhost",
        "shop.localhost,other.localhost",
        "shop.localhost/path",
    ],
)
def test_unknown_or_malformed_host_returns_404(storefront, host):
    assert storefront.client.get("/api/v1/storefront", headers={"Host": host}).status_code == 404


def test_duplicate_host_is_rejected(storefront):
    assert (
        storefront.client.get(
            "/api/v1/storefront", headers=[("Host", storefront.host), ("Host", storefront.host)]
        ).status_code
        == 404
    )


def test_case_normalization_and_different_ports(storefront):
    c = storefront
    assert (
        c.client.get(
            "/api/v1/storefront", headers={"Host": f"{c.business.slug}.LOCALHOST:5173"}
        ).status_code
        == 200
    )


@pytest.mark.parametrize("params", [{"page": 0}, {"page_size": 101}, {"q": " "}])
def test_public_query_validation(storefront, params):
    assert (
        storefront.client.get(
            "/api/v1/storefront/products", headers={"Host": storefront.host}, params=params
        ).status_code
        == 422
    )


def test_search_is_literal_and_pages_are_scoped(storefront):
    c = storefront
    assert (
        c.client.get(
            "/api/v1/storefront/products", headers={"Host": c.host}, params={"q": "%"}
        ).json()["total"]
        == 1
    )
    assert (
        c.client.get(
            "/api/v1/storefront/products", headers={"Host": c.host}, params={"q": "chocolate"}
        ).json()["total"]
        == 1
    )
    result = c.client.get(
        "/api/v1/storefront/products", headers={"Host": c.host}, params={"page": 2}
    ).json()
    assert result["total"] == 1 and result["items"] == []
