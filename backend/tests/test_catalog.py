from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.db.models import Product


def create(context, **changes):
    return context.client.post(
        f"{context.base}/products",
        headers=context.headers,
        json={"name": "Chocolate Cake", "price": "499.00", "description": "Fresh cake", **changes},
    )


def test_business_list_detail_and_partial_update(catalog_context):
    c = catalog_context
    response = c.client.get("/api/v1/admin/businesses")
    assert response.status_code == 200
    assert {item["id"] for item in response.json()["items"]} == {c.business.id, c.sibling.id}
    assert response.json()["total"] == 2
    detail = c.client.get(c.base)
    assert detail.json()["id"] == c.business.id
    assert "owner_id" not in detail.json() and "logo_path" not in detail.json()
    assert detail.headers["cache-control"] == "no-store"
    original = detail.json()
    response = c.client.patch(
        c.base,
        headers=c.headers,
        json={"name": " Changed ", "contact_email": "HELLO@EXAMPLE.COM", "description": "About"},
    )
    assert response.status_code == 200
    assert (
        response.json()["name"] == "Changed"
        and response.json()["contact_email"] == "hello@example.com"
    )
    assert response.json()["slug"] == original["slug"] and response.json()["currency"] == "INR"
    cleared = c.client.patch(c.base, headers=c.headers, json={"description": None})
    assert cleared.json()["description"] is None and cleared.json()["name"] == "Changed"


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"name": None},
        {"name": " "},
        {"slug": "new"},
        {"currency": "USD"},
        {"owner_id": "other"},
        {"logo_path": "file"},
        {"contact_email": "bad"},
        {"description": "x" * 5001},
        {"address": "x" * 1001},
    ],
)
def test_business_update_validation(catalog_context, body):
    c = catalog_context
    before = c.client.get(c.base).json()
    assert c.client.patch(c.base, headers=c.headers, json=body).status_code == 422
    assert c.client.get(c.base).json() == before


def test_product_lifecycle(catalog_context):
    c = catalog_context
    response = create(c)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "draft" and body["price"] == "499.00" and body["image_url"] is None
    assert body["business_id"] == c.business.id and "image_path" not in body
    path = f"{c.base}/products/{body['id']}"
    assert c.client.get(path).json() == body
    changed = c.client.patch(path, headers=c.headers, json={"status": "published", "price": "0.10"})
    assert changed.status_code == 200 and changed.json()["price"] == "0.10"
    assert changed.json()["description"] == "Fresh cake" and changed.json()["status"] == "published"
    assert c.db.get(Product, body["id"]).price == Decimal("0.10")
    changed = c.client.patch(path, headers=c.headers, json={"status": "draft", "description": None})
    assert changed.json()["description"] is None and changed.json()["status"] == "draft"
    deleted = c.client.delete(path, headers=c.headers)
    assert deleted.status_code == 204 and deleted.content == b""
    assert c.client.get(path).status_code == 404


@pytest.mark.parametrize(
    "price", ["-1", "1.001", "NaN", "Infinity", "1e2", "10000000000.00", " 1.00 ", 1.5, True, None]
)
def test_product_rejects_invalid_prices_on_create_and_patch(catalog_context, price):
    c = catalog_context
    item = create(c).json()
    assert create(c, price=price).status_code == 422
    assert (
        c.client.patch(
            f"{c.base}/products/{item['id']}", headers=c.headers, json={"price": price}
        ).status_code
        == 422
    )


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"name": None},
        {"name": " "},
        {"status": None},
        {"status": "hidden"},
        {"business_id": "other"},
        {"image_path": "file"},
        {"id": "other"},
    ],
)
def test_product_patch_rejects_invalid_fields(catalog_context, body):
    c = catalog_context
    item = create(c).json()
    assert (
        c.client.patch(f"{c.base}/products/{item['id']}", headers=c.headers, json=body).status_code
        == 422
    )


def test_product_create_cannot_publish_or_assign_owner(catalog_context):
    assert create(catalog_context, status="published").status_code == 422
    assert create(catalog_context, business_id="other").status_code == 422


@pytest.mark.parametrize(
    "price,expected", [("0", "0.00"), ("0.1", "0.10"), ("9999999999.99", "9999999999.99")]
)
def test_price_boundaries_round_trip_exactly(catalog_context, price, expected):
    c = catalog_context
    response = create(c, price=price)
    assert response.status_code == 201 and response.json()["price"] == expected
    assert c.client.get(f"{c.base}/products/{response.json()['id']}").json()["price"] == expected


def test_search_filter_pagination_and_tie_breaking(catalog_context):
    c = catalog_context
    items = [
        Product(
            id=str(uuid4()),
            business_id=c.business.id,
            name=name,
            description=description,
            price=Decimal("0.00"),
            status=status,
            created_at=datetime(2030, 1, 1),
        )
        for name, description, status in [
            ("Cake 100%", "chocolate", "draft"),
            ("Cake", "Vanilla", "published"),
            ("Bread", "Sourdough", "draft"),
        ]
    ]
    c.db.add_all(items)
    c.db.add(Product(business_id=c.foreign.id, name="Cake", price=Decimal("1.00")))
    c.db.commit()
    path = f"{c.base}/products"
    response = c.client.get(path, params={"q": "CAKE", "page_size": 1, "page": 1})
    assert response.status_code == 200 and response.json()["total"] == 2
    next_page = c.client.get(path, params={"q": "CAKE", "page_size": 1, "page": 2}).json()
    assert response.json()["items"][0]["id"] > next_page["items"][0]["id"]
    assert c.client.get(path, params={"q": "%"}).json()["total"] == 1
    assert c.client.get(path, params={"q": "vanilla", "status": "published"}).json()["total"] == 1
    assert c.client.get(path, params={"status": "draft"}).json()["total"] == 2
    assert c.client.get(path, params={"page": 100}).json()["items"] == []
    assert c.client.get(f"/api/v1/admin/businesses/{c.sibling.id}/products").json()["total"] == 0


@pytest.mark.parametrize("params", [{"page": 0}, {"page_size": 101}, {"status": "all"}, {"q": " "}])
def test_invalid_list_queries(catalog_context, params):
    assert (
        catalog_context.client.get(f"{catalog_context.base}/products", params=params).status_code
        == 422
    )


def test_cross_business_paths_fail_for_every_operation(catalog_context):
    c = catalog_context
    foreign_product = Product(business_id=c.foreign.id, name="Private", price=Decimal("1.00"))
    sibling_product = Product(business_id=c.sibling.id, name="Sibling", price=Decimal("2.00"))
    c.db.add_all([foreign_product, sibling_product])
    c.db.commit()
    for business_id, product_id in [
        (c.foreign.id, foreign_product.id),
        (c.business.id, foreign_product.id),
        (c.business.id, sibling_product.id),
        (c.business.id, str(uuid4())),
    ]:
        product_url = f"/api/v1/admin/businesses/{business_id}/products/{product_id}"
        for method, body in [("GET", None), ("PATCH", {"name": "Hacked"}), ("DELETE", None)]:
            response = c.client.request(method, product_url, json=body, headers=c.headers)
            assert response.status_code == 404
    foreign_url = f"/api/v1/admin/businesses/{c.foreign.id}"
    assert c.client.get(foreign_url).status_code == 404
    assert (
        c.client.patch(foreign_url, headers=c.headers, json={"name": "Hacked"}).status_code == 404
    )
    assert c.client.get(f"{foreign_url}/products").status_code == 404
    assert (
        c.client.post(
            f"{foreign_url}/products", headers=c.headers, json={"name": "Hacked", "price": "1.00"}
        ).status_code
        == 404
    )
    assert c.db.get(Product, foreign_product.id).name == "Private"
    assert c.db.get(Product, sibling_product.id).name == "Sibling"


@pytest.mark.parametrize("state", ["missing", "csrf", "origin"])
def test_catalog_protection(catalog_context, state):
    c = catalog_context
    item = create(c).json()
    request_headers = dict(c.headers)
    if state == "missing":
        c.client.cookies.clear()
    elif state == "csrf":
        request_headers.pop("X-CSRF-Token")
    else:
        request_headers["Origin"] = "https://evil.example.com"
    for method, path, body in [
        ("PATCH", c.base, {"name": "Changed"}),
        ("POST", f"{c.base}/products", {"name": "Changed", "price": "1.00"}),
        ("PATCH", f"{c.base}/products/{item['id']}", {"name": "Changed"}),
        ("DELETE", f"{c.base}/products/{item['id']}", None),
    ]:
        assert c.client.request(method, path, headers=request_headers, json=body).status_code == (
            401 if state == "missing" else 403
        )
    if state == "missing":
        for path in [
            "/api/v1/admin/businesses",
            c.base,
            f"{c.base}/products",
            f"{c.base}/products/{item['id']}",
        ]:
            assert c.client.get(path).status_code == 401


@pytest.mark.parametrize("operation", ["business", "create", "update", "delete"])
def test_mutation_commit_failure_rolls_back(catalog_context, monkeypatch, operation):
    c = catalog_context
    item = create(c).json()
    before = c.client.get(c.base).json()

    def fail():
        raise OperationalError("private SQL", {}, Exception("private credentials"))

    monkeypatch.setattr(c.db, "commit", fail)
    method, path, body = {
        "business": ("PATCH", c.base, {"name": "Changed"}),
        "create": ("POST", f"{c.base}/products", {"name": "Changed", "price": "1.00"}),
        "update": ("PATCH", f"{c.base}/products/{item['id']}", {"name": "Changed"}),
        "delete": ("DELETE", f"{c.base}/products/{item['id']}", None),
    }[operation]
    response = c.client.request(method, path, headers=c.headers, json=body)
    assert response.status_code == 503 and "private" not in response.text
    assert c.client.get(c.base).json() == before
    assert c.client.get(f"{c.base}/products/{item['id']}").json() == item
    assert len(c.db.scalars(select(Product).where(Product.business_id == c.business.id)).all()) == 1
