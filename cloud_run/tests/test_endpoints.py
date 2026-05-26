"""Integration smoke for the FastAPI app — all 13 endpoints reachable + multi-tenant isolation."""
from app.services import bq_client
from app.services.firestore_client import user_col


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["ok"]


def test_auth_required(client):
    r = client.post("/api/search", json={"keyword": "x"})
    assert r.status_code == 401


def test_search_tier1(client, auth_headers, seed_user_data):
    bq_client.set_fake_rows([
        {"report_no": "R1", "name": "BrandAlpha Gold", "company": "TestMfgCo", "type": "supplement", "kg24": 1000},
        {"report_no": "R2", "name": "BrandAlpha Kids", "company": "TestMfgCo", "type": "supplement", "kg24": 500},
        {"report_no": "R3", "name": "alphaprobio drink", "company": "OtherCo", "type": "beverage", "kg24": 9000},
    ])
    r = client.post("/api/search", json={"keyword": "category_alpha", "topN": 5}, headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["success"] and data["tier"] == 1
    assert data["category"] == "category_alpha"
    # BrandAlpha should be matched; the beverage row excluded by exclude_keywords or item_type filter
    brands = {b["brand"] for b in data["mapped_brands"]}
    assert "BrandAlpha" in brands
    assert data["mapping_coverage"] > 0


def test_search_tier0(client, auth_headers):
    bq_client.set_fake_rows([
        {"report_no": "R4", "name": "omega-3 capsule", "company": "CoA", "type": "supplement", "kg24": 100},
    ])
    r = client.post("/api/search", json={"keyword": "omega-3", "topN": 5}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["tier"] == 0


def test_search_empty(client, auth_headers):
    r = client.post("/api/search", json={"keyword": "  ", "topN": 5}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["success"] is False


def test_favorites_crud(client, auth_headers):
    add = client.post("/api/favorites", json={"keyword": "collagen", "frequency": "weekly"}, headers=auth_headers)
    assert add.status_code == 200 and add.json()["success"]
    lst = client.get("/api/favorites", headers=auth_headers).json()
    assert any(f["keyword"] == "collagen" for f in lst["favorites"])
    rm = client.delete("/api/favorites/collagen", headers=auth_headers)
    assert rm.json()["deleted"] >= 1


def test_history_endpoint(client, auth_headers, seed_user_data):
    bq_client.set_fake_rows([{"report_no": "R1", "name": "BrandAlpha", "company": "X", "type": "supplement", "kg24": 100}])
    client.post("/api/search", json={"keyword": "category_alpha", "topN": 3}, headers=auth_headers)
    r = client.get("/api/search-history?daysBack=7", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["success"] and len(r.json()["history"]) >= 1


def test_timeseries_insufficient(client, auth_headers):
    r = client.get("/api/timeseries?category=category_alpha&monthsBack=12", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["success"]
    assert data["count"] == 0
    assert data["insufficient"]


def test_cagr_insufficient(client, auth_headers):
    r = client.get("/api/cagr?category=category_alpha&periodMonths=12", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["insufficient"]


def test_yoy_insufficient(client, auth_headers):
    r = client.get("/api/yoy?category=category_alpha", headers=auth_headers)
    assert r.json()["insufficient"]


def test_pricing_missing(client, auth_headers):
    r = client.get("/api/category-pricing?category=category_alpha", headers=auth_headers)
    assert r.json()["success"] is False and r.json()["error"] == "no_pricing_data"


def test_market_size_missing(client, auth_headers, seed_user_data):
    r = client.get("/api/market-size?category=category_alpha", headers=auth_headers)
    assert r.json()["success"] is False


def test_analytics(client, auth_headers):
    r = client.get("/api/analytics?daysBack=30", headers=auth_headers)
    assert r.status_code == 200 and r.json()["success"]


def test_brand_compare(client, auth_headers):
    r = client.post("/api/brand-compare",
                    json={"brands": ["BrandAlpha", "BrandBeta"], "periodMonths": 6},
                    headers=auth_headers)
    assert r.json()["success"] and r.json()["insufficient"]


def test_export_csv(client, auth_headers, seed_user_data):
    bq_client.set_fake_rows([
        {"report_no": "R1", "name": "BrandAlpha Gold", "company": "TestMfgCo", "type": "supplement", "kg24": 1000},
    ])
    r = client.get("/api/export-csv/search?keyword=category_alpha&topN=5", headers=auth_headers)
    assert r.status_code == 200
    body = r.text
    assert "rank" in body and "BrandAlpha" in body


def test_tenant_isolation(client, auth_headers):
    """Favorites for uid42 must not leak to a different uid."""
    client.post("/api/favorites", json={"keyword": "secret"}, headers=auth_headers)
    other = {"Authorization": "Bearer test-otheruid-other@example.com"}
    r = client.get("/api/favorites", headers=other)
    assert all(f["keyword"] != "secret" for f in r.json()["favorites"])
