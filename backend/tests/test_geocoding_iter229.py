"""Iter 229 — server-side geocoding, provenance, property→building fallback.

Unit tests (no live Google, no Publish). Live preview tests are skipped when
GOOGLE_MAPS_SERVER_API_KEY is absent.
"""
import asyncio
import os
from unittest.mock import AsyncMock, MagicMock

import pytest


def _run(coro):
    return asyncio.run(coro)

from geocoding import (
    SOURCE_GOOGLE,
    STATUS_NEEDS_VERIFICATION,
    STATUS_NEVERIFICAT,
    STATUS_UNCONFIGURED,
    STATUS_UNAVAILABLE,
    STATUS_INSUFFICIENT_ADDRESS,
    address_is_sufficient,
    building_location_update,
    compose_geocode_query,
    coords_are_protected,
    geocode_address,
    has_stored_coords,
    normalize_address,
    property_location_update,
    should_write_coords,
)
from location_resolver import (
    extract_building_location,
    resolve_listing_map_location,
    resolve_property_map_location,
)


NEGOIU = "Aleea Negoiu nr 8D, Cluj-Napoca, 400676, România"


class TestNormalize:
    def test_8d_compact(self):
        assert "8D" in normalize_address("Aleea Negoiu nr 8D")

    def test_8_space_d(self):
        out = normalize_address("Aleea Negoiu nr 8 D")
        assert "8D" in out
        assert "8 D" not in out

    def test_8_d_scara_keeps_building(self):
        out = normalize_address("Aleea Negoiu nr 8 D, sc 2")
        assert "8D" in out
        assert "sc 2" not in out.lower()
        assert "Negoiu" in out

    def test_scara_without_comma(self):
        out = normalize_address("Aleea Negoiu nr 8D sc 2")
        assert "8D" in out
        assert "sc 2" not in out.lower()

    def test_compose_includes_city_postal(self):
        q = compose_geocode_query("Aleea Negoiu nr 8 D sc 2", city="Cluj-Napoca", postal_code="400676")
        assert "8D" in q
        assert "Cluj-Napoca" in q
        assert "400676" in q
        assert "sc 2" not in q.lower()


class TestSufficient:
    def test_negoiu_8d(self):
        assert address_is_sufficient(NEGOIU)

    def test_negoiu_short(self):
        assert address_is_sufficient("Aleea Negoiu nr 8D", "Cluj-Napoca")

    def test_incomplete_street_only(self):
        assert not address_is_sufficient("Aleea Negoiu ", "Aleea Negoiu")

    def test_city_only(self):
        assert not address_is_sufficient("cluj", "cluj")

    def test_aviatorilor_no_number(self):
        assert not address_is_sufficient("Bd. Aviatorilor, Sector 1", "București")


def _google_client(payload):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = payload
    client = AsyncMock()
    client.get = AsyncMock(return_value=resp)
    return client


class TestClassifyAndGeocode:
    def test_unconfigured_without_key(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_MAPS_SERVER_API_KEY", raising=False)
        out = _run(geocode_address(NEGOIU))
        assert out["verification_status"] == STATUS_UNCONFIGURED
        assert out["lat"] is None

    def test_insufficient_does_not_call_google(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_MAPS_SERVER_API_KEY", "test-server-key")
        client = AsyncMock()
        out = _run(geocode_address("cluj", client=client))
        assert out["verification_status"] == STATUS_INSUFFICIENT_ADDRESS
        client.get.assert_not_called()

    def test_single_rooftop_accepted(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_MAPS_SERVER_API_KEY", "test-server-key")
        client = _google_client({
            "status": "OK",
            "results": [{
                "geometry": {
                    "location": {"lat": 46.750123, "lng": 23.546789},
                    "location_type": "ROOFTOP",
                },
                "place_id": "abc",
                "formatted_address": "Aleea Negoiu 8D, Cluj-Napoca, Romania",
            }],
        })
        out = _run(geocode_address(NEGOIU, client=client))
        assert out["lat"] == pytest.approx(46.750123)
        assert out["lng"] == pytest.approx(23.546789)
        assert out["source"] == SOURCE_GOOGLE
        assert out["verification_status"] == STATUS_NEVERIFICAT
        assert out["derived_from"] == "address"
        assert out["method"] == "geocoding"
        assert out["geocoded_at"]
        _args, kwargs = client.get.call_args
        assert kwargs["params"]["key"] == "test-server-key"
        assert "8D" in kwargs["params"]["address"] or "Negoiu" in kwargs["params"]["address"]

    def test_multiple_results_not_picked(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_MAPS_SERVER_API_KEY", "test-server-key")
        client = _google_client({
            "status": "OK",
            "results": [
                {"geometry": {"location": {"lat": 46.75, "lng": 23.54}, "location_type": "ROOFTOP"}},
                {"geometry": {"location": {"lat": 46.76, "lng": 23.55}, "location_type": "ROOFTOP"}},
            ],
        })
        out = _run(geocode_address(NEGOIU, client=client))
        assert out["lat"] is None
        assert out["verification_status"] == STATUS_NEEDS_VERIFICATION
        assert "ambiguous" in (out.get("reason") or "")

    def test_approximate_not_picked(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_MAPS_SERVER_API_KEY", "test-server-key")
        client = _google_client({
            "status": "OK",
            "results": [{
                "geometry": {
                    "location": {"lat": 46.77, "lng": 23.59},
                    "location_type": "APPROXIMATE",
                },
            }],
        })
        out = _run(geocode_address("Aleea Negoiu nr 8D, Cluj-Napoca", client=client))
        assert out["lat"] is None
        assert out["verification_status"] == STATUS_NEEDS_VERIFICATION

    def test_request_denied_not_masked_as_zero_results(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_MAPS_SERVER_API_KEY", "test-server-key")
        client = _google_client({
            "status": "REQUEST_DENIED",
            "error_message": "You must enable Billing on the Google Cloud Project",
            "results": [],
        })
        out = _run(geocode_address(NEGOIU, client=client))
        assert out["lat"] is None
        assert out["verification_status"] == STATUS_UNAVAILABLE
        assert "REQUEST_DENIED" in (out.get("reason") or "")
        assert "zero_results" not in (out.get("reason") or "")
        monkeypatch.setenv("GOOGLE_MAPS_SERVER_API_KEY", "test-server-key")
        client = _google_client({"status": "ZERO_RESULTS", "results": []})
        out = _run(geocode_address(NEGOIU, client=client))
        assert out["verification_status"] == STATUS_UNAVAILABLE
        assert out["lat"] is None

    def test_key_not_in_exception_log(self, monkeypatch, caplog):
        monkeypatch.setenv("GOOGLE_MAPS_SERVER_API_KEY", "super-secret-server-key")
        client = AsyncMock()
        client.get = AsyncMock(side_effect=RuntimeError("boom key=super-secret-server-key"))
        with caplog.at_level("WARNING", logger="propmanage.geocoding"):
            out = _run(geocode_address(NEGOIU, client=client))
        assert out["verification_status"] == STATUS_UNAVAILABLE
        joined = " ".join(r.message for r in caplog.records)
        assert "super-secret-server-key" not in joined


class TestProvenanceWrite:
    def test_never_overwrite_verified(self):
        entity = {"lat": 1.0, "lng": 2.0, "location": {
            "lat": 1.0, "lng": 2.0, "source": "manual",
            "verification_status": "verified",
        }}
        cand = {"lat": 9.0, "lng": 9.0, "source": SOURCE_GOOGLE, "verification_status": STATUS_NEVERIFICAT}
        assert coords_are_protected(entity)
        assert not should_write_coords(entity, cand)

    def test_never_overwrite_existing_unverified(self):
        entity = {"lat": 1.0, "lng": 2.0, "location": {
            "source": "manual", "verification_status": "neverificat",
        }}
        cand = {"lat": 9.0, "lng": 9.0}
        assert has_stored_coords(entity)
        assert not should_write_coords(entity, cand)

    def test_write_when_empty(self):
        entity = {"address": NEGOIU}
        cand = {"lat": 46.75, "lng": 23.54}
        assert should_write_coords(entity, cand)

    def test_building_hb_coords_protected_from_overwrite(self):
        b = {"context": {
            "lat": 46.7495, "lng": 23.55,
            "verification_status": "unverified",
            "external_sources": {"hartablocuri": {
                "verification_status": "neverificat",
                "raw": {"lat": 46.7495, "lng": 23.55},
            }},
        }}
        cand = {"lat": 1.0, "lng": 1.0}
        assert has_stored_coords(b)
        assert not should_write_coords(b, cand)

    def test_building_update_uses_external_sources(self):
        b = {"context": {"verification_status": "unverified"}}
        cand = {"lat": 46.75, "lng": 23.54, "source": SOURCE_GOOGLE,
                "verification_status": STATUS_NEVERIFICAT, "derived_from": "address",
                "method": "geocoding", "query": NEGOIU}
        upd = building_location_update(b, cand)
        ctx = upd["context"]
        assert ctx["lat"] == 46.75
        gg = ctx["external_sources"][SOURCE_GOOGLE]
        assert gg["verification_status"] == STATUS_NEVERIFICAT
        assert gg["source_name"] == SOURCE_GOOGLE
        assert ctx["verification_status"] == "unverified"  # whole-building status unchanged

    def test_property_update_keeps_toplevel_latlng(self):
        cand = {"lat": 46.75, "lng": 23.54, "source": SOURCE_GOOGLE,
                "verification_status": STATUS_NEVERIFICAT, "derived_from": "address",
                "method": "geocoding"}
        upd = property_location_update(cand)
        assert upd["lat"] == 46.75
        assert upd["location"]["source"] == SOURCE_GOOGLE
        assert upd["location"]["verification_status"] == STATUS_NEVERIFICAT


class TestResolverPriority:
    def test_property_verified_wins(self):
        prop = {"lat": 1.0, "lng": 2.0, "location": {
            "lat": 1.0, "lng": 2.0, "source": "manual",
            "verification_status": "verified", "derived_from": "property",
        }}
        building = {"context": {
            "lat": 46.7, "lng": 23.5, "verification_status": "verified",
            "external_sources": {"hartablocuri": {"verification_status": "neverificat",
                                                  "raw": {"lat": 46.7, "lng": 23.5}}},
        }}
        r = resolve_property_map_location(prop, building)
        assert r["lat"] == 1.0
        assert r["priority"] == 1
        assert not r.get("derived")

    def test_property_manual_unverified_beats_building(self):
        prop = {"lat": 1.1, "lng": 2.2, "location": {
            "source": "manual", "verification_status": "neverificat",
        }}
        building = {"_id": "b1", "context": {
            "lat": 46.7, "lng": 23.5,
            "external_sources": {"hartablocuri": {
                "verification_status": "neverificat", "raw": {"lat": 46.7, "lng": 23.5},
            }},
        }}
        r = resolve_property_map_location(prop, building)
        assert r["lat"] == pytest.approx(1.1)
        assert r["priority"] == 2

    def test_building_hb_fallback_not_copied(self):
        prop = {"address": "manastur allea negoi", "building_id": "b1"}
        building = {"_id": "b1", "context": {
            "lat": 46.7495, "lng": 23.551,
            "verification_status": "unverified",
            "external_sources": {"hartablocuri": {
                "verification_status": "neverificat",
                "raw": {"lat": 46.7495, "lng": 23.551},
            }},
        }}
        r = resolve_property_map_location(prop, building)
        assert r["available"]
        assert r["derived"] is True
        assert r["source"] == "hartablocuri"
        assert r["verification_status"] == "neverificat"
        assert r["derived_from"] == "building"
        assert "HartaBlocuri" in (r.get("provenance_label") or "")
        # property document unchanged
        assert prop.get("lat") is None

    def test_building_geocoding_fallback(self):
        prop = {"address": "Aleea Negoiu nr 8D"}
        building = {"_id": "b1", "context": {
            "lat": 46.75, "lng": 23.54, "verification_status": "unverified",
            "external_sources": {SOURCE_GOOGLE: {
                "source_name": SOURCE_GOOGLE, "verification_status": STATUS_NEVERIFICAT,
                "lat": 46.75, "lng": 23.54, "derived_from": "address", "method": "geocoding",
            }},
        }}
        r = resolve_property_map_location(prop, building)
        assert r["available"]
        assert r["derived"]
        assert r["source"] == SOURCE_GOOGLE

    def test_no_coords(self):
        r = resolve_property_map_location({"address": "cluj"}, None)
        assert r["available"] is False
        assert r["lat"] is None

    def test_listing_uses_building_fallback(self):
        listing = {"title": "Imobil în pregătire · Aleea Negoiu", "address": "Aleea Negoiu "}
        building = {"_id": "b1", "context": {
            "lat": 46.75, "lng": 23.54,
            "external_sources": {SOURCE_GOOGLE: {
                "lat": 46.75, "lng": 23.54, "verification_status": STATUS_NEVERIFICAT,
                "source_name": SOURCE_GOOGLE,
            }},
        }}
        r = resolve_listing_map_location(listing, None, building)
        assert r["available"]
        assert r["derived"]
        assert listing.get("lat") is None  # not copied onto listing

    def test_extract_building_hb(self):
        b = {"_id": "x", "context": {
            "lat": 46.7496, "lng": 23.55,
            "external_sources": {"hartablocuri": {
                "verification_status": "neverificat",
                "raw": {"lat": 46.7496, "lng": 23.55},
            }},
        }}
        loc = extract_building_location(b)
        assert loc["source"] == "hartablocuri"
        assert loc["verification_status"] == "neverificat"


@pytest.mark.skipif(not os.environ.get("GOOGLE_MAPS_SERVER_API_KEY"),
                    reason="live geocoding requires GOOGLE_MAPS_SERVER_API_KEY")
class TestLiveNegoIu:
    def test_live_aleya_negoiu_8d(self):
        out = _run(geocode_address(NEGOIU))
        assert out.get("verification_status") in (
            STATUS_NEVERIFICAT, STATUS_NEEDS_VERIFICATION, STATUS_UNAVAILABLE)
        if out.get("lat") is not None:
            assert 46.6 < out["lat"] < 46.9
            assert 23.4 < out["lng"] < 23.8
            assert out["source"] == SOURCE_GOOGLE
            assert out["verification_status"] == STATUS_NEVERIFICAT
