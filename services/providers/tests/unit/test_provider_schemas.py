"""Unit tests for provider schema mapping and API behaviour."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from providers.main import app
from providers.schemas.provider import ProviderOut, ProviderSearchResponse


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


# ── ProviderOut ───────────────────────────────────────────────────────────────

def test_provider_out_individual() -> None:
    p = ProviderOut(
        id=uuid.uuid4(),
        npi="1234567890",
        firstName="Jordan",
        lastName="Chen",
        organizationName=None,
        credentialText="MD",
        taxonomyCode="207Q00000X",
        taxonomyDescription="Family Medicine",
        addressLine1="100 Main St",
        city="Springfield",
        state="IL",
        zip="62701",
        phone="2175551234",
        acceptingNewPatients=True,
        qualityRating=4.5,
        hospitalName=None,
        specialtyCodes=["207Q00000X"],
    )
    assert p.npi == "1234567890"
    assert p.qualityRating == 4.5
    assert p.acceptingNewPatients is True


def test_provider_out_organization() -> None:
    p = ProviderOut(
        id=uuid.uuid4(),
        npi="9876543210",
        firstName=None,
        lastName=None,
        organizationName="City Medical Group",
        credentialText=None,
        taxonomyCode=None,
        taxonomyDescription=None,
        addressLine1=None,
        city=None,
        state="CA",
        zip=None,
        phone=None,
        acceptingNewPatients=None,
        qualityRating=None,
        hospitalName="City Hospital",
        specialtyCodes=None,
    )
    assert p.organizationName == "City Medical Group"
    assert p.qualityRating is None


def test_provider_search_response_empty() -> None:
    r = ProviderSearchResponse(total=0, providers=[])
    assert r.total == 0
    assert r.providers == []


def test_provider_search_response_count_matches() -> None:
    providers = [
        ProviderOut(
            id=uuid.uuid4(),
            npi=f"100000000{i}",
            firstName=None,
            lastName=f"Doctor{i}",
            organizationName=None,
            credentialText="MD",
            taxonomyCode=None,
            taxonomyDescription="Cardiology",
            addressLine1=None,
            city=None,
            state="NY",
            zip=None,
            phone=None,
            acceptingNewPatients=True,
            qualityRating=3.0,
            hospitalName=None,
            specialtyCodes=None,
        )
        for i in range(3)
    ]
    r = ProviderSearchResponse(total=len(providers), providers=providers)
    assert r.total == 3
    assert len(r.providers) == 3


# ── API 404 / search behaviour (mock DB) ─────────────────────────────────────

def test_provider_detail_404(client: TestClient) -> None:
    with patch(
        "providers.api.v1.providers.get_provider_by_npi",
        return_value=None,
    ):
        with patch("providers.api.v1.providers.db_session") as mock_ctx:
            mock_session = MagicMock()
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            resp = client.get("/api/v1/providers/0000000000")

    assert resp.status_code == 404
    assert "0000000000" in resp.json()["detail"]


def test_provider_search_empty_results(client: TestClient) -> None:
    with patch(
        "providers.api.v1.providers.search_providers",
        return_value=[],
    ):
        with patch("providers.api.v1.providers.db_session") as mock_ctx:
            mock_session = MagicMock()
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            resp = client.get("/api/v1/providers/search?specialty=neurology&state=WY")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["providers"] == []


def test_provider_search_returns_results(client: TestClient) -> None:
    fake_row = {
        "id": uuid.uuid4(),
        "npi": "1111111111",
        "first_name": "Pat",
        "last_name": "Smith",
        "organization_name": None,
        "credential_text": "DO",
        "taxonomy_code": "207R00000X",
        "taxonomy_description": "Internal Medicine",
        "practice_location_address_line_1": "200 Oak Ave",
        "practice_location_city": "Denver",
        "practice_location_state": "CO",
        "practice_location_zip": "80201",
        "practice_location_phone": "3035559876",
        "accepting_new_patients": True,
        "quality_rating": 4.0,
        "hospital_name": None,
        "specialty_codes": ["207R00000X"],
    }
    with patch(
        "providers.api.v1.providers.search_providers",
        return_value=[fake_row],
    ):
        with patch("providers.api.v1.providers.db_session") as mock_ctx:
            mock_session = MagicMock()
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            resp = client.get("/api/v1/providers/search?specialty=internal+medicine&state=CO")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["providers"][0]["npi"] == "1111111111"
    assert data["providers"][0]["qualityRating"] == 4.0
