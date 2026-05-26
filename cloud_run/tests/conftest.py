"""pytest fixtures — sets TEST_MODE before app import, returns a TestClient."""
import os
os.environ["TEST_MODE"] = "true"

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.firestore_client import db, user_col, init_firestore
from app.services import bq_client


@pytest.fixture(autouse=True)
def reset_backends():
    # Wipe in-memory firestore between tests
    init_firestore()
    d = db()
    if hasattr(d, "_store"): d._store.clear()
    bq_client.set_fake_rows([])
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Test-mode JWT decoder accepts 'test-<uid>-<email>' as bearer."""
    return {"Authorization": "Bearer test-uid42-tester@example.com"}


@pytest.fixture
def seed_user_data():
    """Seed a sample category mapping + brand mappings for uid42 (generic test fixtures)."""
    user_col("uid42", "category_mappings").document().set({
        "tier": 1, "category": "category_alpha",
        "item_type_filter": "supplement",
        "include_keywords": "alpha|alphaprobio|alpharoot",
        "exclude_keywords": "drink|beverage",
        "accuracy_basis": "80%+",
    })
    user_col("uid42", "brand_mappings").document().set({
        "category": "category_alpha", "brand": "BrandAlpha",
        "display_name": "BrandAlpha (TEST)",
        "brand_keywords": "brandalpha|alphaone",
        "seller_keywords": "TestMfgCo",
        "type": "self",
        "revenue_ref": 1000,
        "confidence": "H",
    })
    user_col("uid42", "brand_mappings").document().set({
        "category": "category_alpha", "brand": "BrandBeta",
        "display_name": "BrandBeta",
        "brand_keywords": "brandbeta|betaone",
        "seller_keywords": "",
        "type": "OEM",
        "confidence": "M",
    })
